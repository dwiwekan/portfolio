#!/usr/bin/env python3
"""Generate the static site from data/*.json.

Usage:
    python3 scripts/build.py

Reads data/profile.json, data/projects.json and data/publications.json and
writes plain HTML (no client-side rendering, so ATS parsers, search engines
and AI agents see every word): index.html, projects/<slug>/index.html,
cv/index.html, redirect stubs for old URLs, sitemap.xml, robots.txt and
llms.txt. Pillow is optional; with it, image sizes are read from the files.
"""
import json
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TODAY = date.today()
CV_PDF = "assets/documents/Ida-Bagus-Dwiweka-Naratama-CV.pdf"

# Old URLs kept alive after the rename; each becomes a redirect stub.
REDIRECTS = {
    "projects/scene-graph": "projects/latent-flow-scene-graph/",
    "projects/map-prediction": "projects/uncertainty-map-exploration/",
    "projects/attention-nav": "projects/attention-semantic-navigation/",
    "print": "cv/",
}

try:
    from PIL import Image
except ImportError:  # sizes are optional
    Image = None


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


P = load("profile.json")
PROJECTS = load("projects.json")
PUBS = load("publications.json")
PUB_BY_ID = {p["id"]: p for p in PUBS}
PROJ_BY_SLUG = {p["slug"]: p for p in PROJECTS}
SITE = P["siteUrl"]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def e(s):
    return escape(str(s), quote=True)


def month(ym):
    y, m = ym.split("-")[:2]
    return f"{MONTHS[int(m) - 1]} {y}"


def span(item):
    end = month(item["end"]) if item.get("end") else "Present"
    if item.get("expected"):
        end += " (expected)"
    return f"{month(item['start'])} – {end}"


def img_size(rel):
    if Image is None:
        return None
    try:
        with Image.open(ROOT / rel) as im:
            return im.size
    except OSError:
        return None


def years_experience():
    y, m = map(int, P["careerStart"].split("-"))
    return (TODAY.year - y) + (TODAY.month - m) / 12


def is_first_author(pub):
    return pub["authors"][0] == P["name"]


def authors_html(pub):
    return ", ".join(f"<strong>{e(a)}</strong>" if a == P["name"] else e(a) for a in pub["authors"])


def status_class(status):
    s = status.lower()
    if s == "published":
        return "status-published"
    if s == "accepted":
        return "status-accepted"
    return "status-review"


def venue_line(pub):
    """Full venue string: name (short), location, volume/issue, pages. Empty for a venue kept private during double-blind review."""
    if not pub.get("venue"):
        return ""
    parts = [f"{pub['venue']} ({pub['venueShort']})" if pub["venueShort"] not in pub["venue"] else pub["venue"]]
    if pub.get("location"):
        parts.append(pub["location"])
    if pub.get("volume"):
        vol = f"vol. {pub['volume']}"
        if pub.get("issue"):
            vol += f", no. {pub['issue']}"
        parts.append(vol)
    if pub.get("pages"):
        parts.append(f"pp. {pub['pages']}")
    if pub.get("date"):
        parts.append(month(pub["date"]))
    return ", ".join(parts)


def kicker(proj):
    pub = PUB_BY_ID.get(proj.get("publication"))
    if pub:
        return f"{pub['venueShort']} · {pub['status']}" if pub.get("venueShort") else pub["status"]
    return proj["context"]


def jsonld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=2) + "\n</script>"


def person_ld():
    edu = [
        {"@type": "CollegeOrUniversity", "name": ed["institution"]} for ed in P["education"]
    ]
    return {
        "@type": "Person",
        "@id": SITE + "#person",
        "name": P["name"],
        "givenName": P["givenName"],
        "familyName": P["familyName"],
        "jobTitle": P["currentRole"].split(",")[0],
        "description": P["summary"],
        "email": "mailto:" + P["email"],
        "url": SITE,
        "image": SITE + P["portrait"],
        "address": {"@type": "PostalAddress", "addressLocality": P["location"]["city"], "addressCountry": P["location"]["countryCode"]},
        "affiliation": {"@type": "Organization", "name": P["experience"][0]["organization"]},
        "alumniOf": edu,
        "knowsAbout": P["focusAreas"] + [i for s in P["skills"] for i in s["items"]],
        "knowsLanguage": [l["language"] for l in P["languages"]],
        "sameAs": [l["url"] for l in P["links"]],
    }


def scholarly_ld(pub, url=None):
    obj = {
        "@type": "ScholarlyArticle",
        "headline": pub["title"],
        "name": pub["title"],
        "author": [{"@type": "Person", "name": a} for a in pub["authors"]],
        "creativeWorkStatus": pub["status"],
    }
    if pub.get("venue"):
        obj["isPartOf"] = {"@type": "Periodical" if pub["type"] == "journal" else "Event", "name": pub["venue"]}
    if pub.get("date"):
        obj["datePublished"] = pub["date"]
    elif pub.get("year"):
        obj["datePublished"] = str(pub["year"])
    if pub.get("pages"):
        obj["pagination"] = pub["pages"]
    if pub.get("doi"):
        obj["sameAs"] = "https://doi.org/" + pub["doi"]
    if url:
        obj["url"] = url
    return obj


# ─── page shell ──────────────────────────────────────────────────────────────

def page(*, path, title, description, body, pre, og_image=None, og_type="website", ld=None, extra_head=""):
    """path: site-relative output directory ('' for home). pre: relative prefix to the site root."""
    url = SITE + path
    og_image = SITE + (og_image or P["portrait"])
    nav = [("Projects", "#projects"), ("Publications", "#publications"), ("Experience", "#experience"),
           ("Education", "#education"), ("Contact", "#contact")]
    nav_html = "\n".join(f'      <a href="{pre}{h}">{t}</a>' if pre else f'      <a href="{h}">{t}</a>' for t, h in nav)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="author" content="{e(P['name'])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(P['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(og_image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(og_image)}">
<link rel="icon" href="{pre}assets/icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{pre}assets/icons/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{pre}assets/icons/apple-touch-icon.png">
<link rel="alternate" type="text/plain" href="{pre}llms.txt" title="Plain-text profile for AI agents">
<link rel="stylesheet" href="{pre}assets/design-system/styles.css">
<link rel="stylesheet" href="{pre}assets/css/site.css">
{extra_head}{jsonld(ld) if ld else ''}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <nav class="nav" aria-label="Main">
      <span class="nav-brand"><a href="{pre or './'}">{e(P['shortName'])}</a></span>
{nav_html}
      <a class="btn btn-primary" href="{pre}{CV_PDF}" type="application/pdf">CV</a>
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <span>© {TODAY.year} {e(P['name'])} · {e(P['location']['city'])}, {e(P['location']['country'])}</span>
    <span><a href="mailto:{e(P['email'])}">{e(P['email'])}</a> · {' · '.join(f'<a href="{e(l["url"])}" rel="me">{e(l["label"])}</a>' for l in P['links'])} · <a href="{pre}llms.txt">llms.txt</a></span>
  </div>
</footer>
</body>
</html>
"""


# ─── home ────────────────────────────────────────────────────────────────────

def card(proj):
    href = f"projects/{proj['slug']}/"
    cover = f"assets/images/projects/{proj['slug']}/cover.jpg"
    size = img_size(cover)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    fill = " fill" if proj.get("coverFit") == "cover" else ""
    alt = proj["figures"][0]["alt"] if proj.get("figures") else proj["title"]
    tags = "".join(f'<li class="tag tag-neutral">{e(t)}</li>' for t in proj["tags"][:3])
    return f"""      <article class="card elev-sm">
        <a href="{href}" tabindex="-1" aria-hidden="true"><img class="thumb{fill}" src="{cover}" alt=""{dims} loading="lazy" decoding="async"></a>
        <div class="card-inner">
          <p class="card-kicker">{e(kicker(proj))}</p>
          <h3 class="card-title"><a href="{href}">{e(proj['title'])}</a></h3>
          <p class="card-body">{e(proj['summary'])}</p>
          <ul class="tags" aria-label="Topics">{tags}</ul>
          <a class="btn btn-secondary" href="{href}" aria-label="Read more about {e(proj['title'])}">Read more →</a>
        </div>
      </article>"""


def pub_item(pub, pre=""):
    proj = PROJ_BY_SLUG.get(pub.get("project"))
    title = e(pub["title"])
    if proj:
        title = f'<a href="{pre}projects/{proj["slug"]}/">{title}</a>'
    links = []
    if proj:
        links.append(f'<a href="{pre}projects/{proj["slug"]}/">Abstract &amp; figures</a>')
    if pub.get("doi"):
        links.append(f'<a href="https://doi.org/{e(pub["doi"])}">DOI {e(pub["doi"])}</a>')
    return f"""      <li class="pub">
        <div>
          <h3>{title}</h3>
          <p class="authors">{authors_html(pub)}</p>
          {f'<p class="venue">{e(venue_line(pub))}</p>' if venue_line(pub) else ''}
          <p class="pub-links">{' '.join(links)}</p>
        </div>
        <span class="tag status {status_class(pub['status'])}">{e(pub['status'])}</span>
      </li>"""


def job(item):
    bullets = "\n".join(f"            <li>{e(h)}</li>" for h in item["highlights"])
    return f"""      <li class="job">
        <p class="when"><span>{span(item)}</span><span>{e(item['location'])}</span></p>
        <div>
          <h3>{e(item['title'])}</h3>
          <p class="org">{e(item['organization'])}</p>
          <ul>
{bullets}
          </ul>
        </div>
      </li>"""


def build_home():
    research = [p for p in PROJECTS if p["category"] == "research"]
    engineering = [p for p in PROJECTS if p["category"] == "engineering"]
    first = sum(is_first_author(p) for p in PUBS)
    published = sum(p["status"] in ("Published", "Accepted") for p in PUBS)
    yrs = int(years_experience())
    ms = P["education"][0]
    career = month(P["careerStart"])

    focus = "".join(f'<li class="tag tag-outline">{e(f)}</li>' for f in P["focusAreas"])
    socials = "".join(f'\n        <a class="btn btn-secondary" href="{e(l["url"])}" rel="me">{e(l["label"])}</a>' for l in P["links"])
    edu = "\n".join(
        f"""        <div class="edu">
          <h4>{e(ed['degree'])}</h4>
          <p>{e(ed['institution'])}, {e(ed['location'])}</p>
          <p class="when">{span(ed)}</p>
          <p>{'<br>'.join(e(d) for d in ed['details'])}</p>
        </div>""" for ed in P["education"])
    skills = "\n".join(f"          <div><dt>{e(s['category'])}</dt><dd>{e(', '.join(s['items']))}</dd></div>" for s in P["skills"])
    langs = ", ".join(f"{l['language']} ({l['level'].lower()})" for l in P["languages"])

    body = f"""<div class="wrap">
  <section class="hero" aria-labelledby="name">
    <div>
      <p class="eyebrow">{e(P['headline'])} · {e(P['location']['city'])}, {e(P['location']['country'])}</p>
      <h1 id="name">{e(P['name'])}</h1>
      <p class="role">{e(P['currentRole'])}</p>
      <p class="summary">{e(P['intro'])}</p>
      <p class="availability">{e(P['availability'])}.</p>
      <ul class="focus" aria-label="Focus areas">{focus}</ul>
      <div class="actions">
        <a class="btn btn-primary" href="{CV_PDF}" type="application/pdf">View CV (PDF)</a>
        <a class="btn btn-secondary" href="mailto:{e(P['email'])}">{e(P['email'])}</a>{socials}
      </div>
    </div>
    <div class="portrait-wrap"><img class="portrait" src="{P['portrait']}" alt="Portrait of {e(P['name'])}" width="240" height="300"></div>
  </section>

  <dl class="stats" aria-label="At a glance">
    <div><dt>Projects</dt><dd><span class="num">{len(PROJECTS)}</span><span class="note">{len(research)} research · {len(engineering)} engineering</span></dd></div>
    <div><dt>Publications</dt><dd><span class="num">{len(PUBS)}</span><span class="note">{first} first-author · {published} published or accepted</span></dd></div>
    <div><dt>Years of experience</dt><dd><span class="num">{yrs}+</span><span class="note">Research, industry and teaching since {career}</span></dd></div>
    <div><dt>Candidate</dt><dd><span class="num num-word">M.S. in Robotics</span><span class="note">Kwangwoon University · graduating {month(ms['end'])}</span></dd></div>
  </dl>

  <section class="section" id="projects" aria-labelledby="projects-h">
    <div class="section-head"><h2 id="projects-h">Projects</h2><p>Each card opens a page with the abstract, figures and results.</p></div>
    <h3 class="subhead">Research · Robotics &amp; AI Lab, Kwangwoon University</h3>
    <div class="cards">
{chr(10).join(card(p) for p in research)}
    </div>
    <h3 class="subhead">Engineering &amp; earlier work</h3>
    <div class="cards">
{chr(10).join(card(p) for p in engineering)}
    </div>
  </section>

  <section class="section" id="publications" aria-labelledby="publications-h">
    <div class="section-head"><h2 id="publications-h">Publications</h2><p>{len(PUBS)} papers · {first} as first author</p></div>
    <ol class="pubs">
{chr(10).join(pub_item(p) for p in PUBS)}
    </ol>
  </section>

  <section class="section" id="experience" aria-labelledby="experience-h">
    <div class="section-head"><h2 id="experience-h">Experience</h2></div>
    <ol class="timeline">
{chr(10).join(job(x) for x in P['experience'])}
    </ol>
    <h3 class="subhead" style="margin-top:40px">Teaching &amp; mentoring</h3>
    <ol class="timeline">
{chr(10).join(job(x) for x in P['teaching'])}
    </ol>
  </section>

  <section class="section two-col" id="education" aria-label="Education and skills">
    <div>
      <div class="section-head"><h2>Education</h2></div>
{edu}
    </div>
    <div id="skills">
      <div class="section-head"><h2>Skills</h2></div>
      <dl class="skills">
{skills}
          <div><dt>Languages</dt><dd>{e(langs)}</dd></div>
      </dl>
    </div>
  </section>

  <section class="section contact" id="contact" aria-labelledby="contact-h">
    <h2 id="contact-h">Contact</h2>
    <p>{e(P['contactNote'])}</p>
    <div class="actions">
      <a class="btn btn-primary" href="mailto:{e(P['email'])}">{e(P['email'])}</a>{socials}
      <a class="btn btn-ghost" href="{CV_PDF}" type="application/pdf">View CV</a>
    </div>
  </section>
</div>"""

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "ProfilePage", "@id": SITE + "#page", "url": SITE, "name": f"{P['name']} | {P['headline']}",
             "dateModified": TODAY.isoformat(), "mainEntity": {"@id": SITE + "#person"}},
            person_ld(),
            {"@type": "ItemList", "name": "Publications",
             "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                  "item": scholarly_ld(p, SITE + f"projects/{p['project']}/" if p.get("project") else None)}
                                 for i, p in enumerate(PUBS)]},
        ],
    }
    desc = (f"{P['name']}, {P['currentRole']}. {len(PROJECTS)} projects and {len(PUBS)} publications in "
            "computer vision, 3D scene understanding, SLAM and autonomous navigation.")
    return page(path="", pre="", title=f"{P['name']} | {P['headline']}", description=desc,
                body=body, og_type="profile", ld=ld)


# ─── project pages ───────────────────────────────────────────────────────────

def figure_html(fig, pre):
    w, h = fig.get("width"), fig.get("height")
    narrow = ' class="narrow"' if w and h and h > w else ""
    dims = f' width="{w}" height="{h}"' if w and h else ""
    return f"""      <figure>
        <img src="{pre}{fig['src']}" alt="{e(fig['alt'])}"{dims}{narrow} loading="lazy" decoding="async">
        <figcaption>{e(fig['caption'])}</figcaption>
      </figure>"""


def build_project(i, proj):
    pre = "../../"
    pub = PUB_BY_ID.get(proj.get("publication"))
    url = SITE + f"projects/{proj['slug']}/"

    facts = []
    if pub:
        if pub.get("venueShort"):
            facts.append(("Venue", pub["venueShort"]))
        facts.append(("Status", pub["status"]))
    facts += [("Role", proj["role"]), ("When", proj["period"]), ("Where", proj["context"])]
    facts_html = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts)

    abstract = "\n".join(f"      <p>{e(p)}</p>" for p in proj["abstract"])
    media = []
    if proj.get("video"):
        v = proj["video"]
        media.append(f"""      <figure>
        <video controls preload="none" playsinline poster="{pre}{v['poster']}" width="1280" height="720">
          <source src="{pre}{v['src']}" type="video/mp4">
        </video>
        <figcaption>{e(v['caption'])}</figcaption>
      </figure>""")
    media += [figure_html(f, pre) for f in proj.get("figures", [])]

    aside = []
    if proj.get("highlights"):
        rows = "".join(f"<div><dt>{e(h['value'])}</dt><dd>{e(h['label'])}</dd></div>" for h in proj["highlights"])
        aside.append(f'<section><h2>Key results</h2><dl class="metrics">{rows}</dl></section>')
    if pub:
        aside.append(f"""<section><h2>Paper</h2><div class="citation">
        <p><strong>{e(pub['title'])}</strong></p>
        <p>{authors_html(pub)}</p>
        {f'<p><em>{e(venue_line(pub))}</em></p>' if venue_line(pub) else ''}
        <p><span class="tag {status_class(pub['status'])}">{e(pub['status'])}</span></p>
      </div></section>""")
    tags = "".join(f'<li class="tag tag-neutral">{e(t)}</li>' for t in proj["tags"])
    aside.append(f'<section><h2>Topics &amp; tools</h2><ul class="tags">{tags}</ul></section>')
    if proj.get("links"):
        links = "".join(f'<a class="btn btn-secondary" href="{e(l["url"])}">{e(l["label"])}</a>' for l in proj["links"])
        aside.append(f'<section><h2>Links</h2><div class="links">{links}</div></section>')

    prev_p = PROJECTS[i - 1] if i > 0 else None
    next_p = PROJECTS[i + 1] if i + 1 < len(PROJECTS) else None
    pager = ""
    if prev_p:
        pager += f'<a class="prev" href="../{prev_p["slug"]}/"><small>← Previous</small>{e(prev_p["title"])}</a>'
    if next_p:
        pager += f'<a class="next" href="../{next_p["slug"]}/"><small>Next →</small>{e(next_p["title"])}</a>'

    body = f"""<div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="{pre}">Home</a> / <a href="{pre}#projects">Projects</a> / {e(proj['title'])}</nav>
  <article>
    <header class="project-hero">
      <p class="eyebrow">{e(kicker(proj))}</p>
      <h1>{e(proj['title'])}</h1>
      <p class="lede">{e(proj['summary'])}</p>
      <dl class="facts">{facts_html}</dl>
    </header>
    <div class="project-body">
      <div>
        <section class="prose" aria-labelledby="abstract-h">
          <h2 id="abstract-h">{'Abstract' if pub else 'Overview'}</h2>
{abstract}
        </section>
        <div class="media">
{chr(10).join(media)}
        </div>
      </div>
      <aside class="aside" aria-label="Project details">
        {chr(10).join(aside)}
      </aside>
    </div>
  </article>
  <nav class="pager" aria-label="More projects">{pager}</nav>
</div>"""

    cover = f"assets/images/projects/{proj['slug']}/cover.jpg"
    graph = [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Projects", "item": SITE + "#projects"},
            {"@type": "ListItem", "position": 3, "name": proj["title"], "item": url}]},
    ]
    work = {
        "@type": "CreativeWork", "name": proj["title"], "url": url, "abstract": " ".join(proj["abstract"]),
        "description": proj["summary"], "keywords": ", ".join(proj["tags"]), "image": SITE + cover,
        "creator": {"@type": "Person", "@id": SITE + "#person", "name": P["name"], "url": SITE},
    }
    if pub:
        work = {**scholarly_ld(pub, url), "abstract": work["abstract"], "description": work["description"],
                "keywords": work["keywords"], "image": work["image"]}
    graph.append(work)
    title = f"{proj['title']} | {P['name']}"
    return page(path=f"projects/{proj['slug']}/", pre=pre, title=title, description=proj["summary"],
                body=body, og_image=cover, og_type="article", ld={"@context": "https://schema.org", "@graph": graph})


# ─── CV ──────────────────────────────────────────────────────────────────────

CV_CSS = """<style>
  body { background: #e9e8e8; font-size: 10.5pt; line-height: 1.42; }
  .sheet { max-width: 210mm; margin: 24px auto; background: #fff; padding: 16mm 17mm; box-shadow: var(--shadow-md); }
  .cv-bar { max-width: 210mm; margin: 20px auto 0; display: flex; gap: 10px; justify-content: flex-end; padding: 0 8px; }
  .sheet h1 { font-size: 22pt; margin: 0; }
  .sheet .role { margin: 2px 0 6px; font-size: 11.5pt; }
  .sheet .contact { font-size: 9.5pt; margin: 0 0 4px; }
  .sheet a { color: inherit; text-decoration: none; }
  .sheet h2 { font-size: 10pt; letter-spacing: 0.12em; text-transform: uppercase; margin: 14px 0 6px; padding-bottom: 3px;
              border-bottom: 1px solid #201e1d; font-family: var(--font-body); font-weight: 600; }
  .sheet p { margin: 0 0 4px; }
  .entry { margin: 0 0 8px; break-inside: avoid; }
  .entry .top { display: flex; justify-content: space-between; gap: 12px; }
  .entry .top span:last-child { white-space: nowrap; }
  .entry ul { margin: 2px 0 0; padding-left: 1.1em; }
  .entry li { margin: 1px 0; }
  .sheet ol { margin: 0; padding-left: 1.4em; }
  .sheet ol li { margin: 0 0 4px; break-inside: avoid; }
  .skills-cv p { margin: 0 0 2px; display: grid; grid-template-columns: 34mm minmax(0, 1fr); gap: 8px; }
  @page { size: A4; margin: 11mm 12mm; }
  @media print {
    body { background: #fff; }
    .site-header, .site-footer, .cv-bar, .skip { display: none !important; }
    .sheet { margin: 0; padding: 0; box-shadow: none; max-width: none; }
    .sheet { font-size: 9.4pt; line-height: 1.34; }
    .sheet h1 { font-size: 19pt; }
    .sheet h2 { margin: 10px 0 5px; font-size: 9pt; }
    .entry { margin-bottom: 6px; }
  }
</style>
"""


def cv_entry(title, org, when, place, bullets=(), details=()):
    lines = "".join(f"<li>{e(b)}</li>" for b in bullets)
    det = "".join(f"<p>{e(d)}</p>" for d in details)
    return f"""    <div class="entry">
      <div class="top"><span><strong>{e(title)}</strong>, {e(org)} <span class="text-muted">· {e(place)}</span></span><span>{e(when)}</span></div>
      {det}{f'<ul>{lines}</ul>' if lines else ''}
    </div>"""


def build_cv():
    pre = "../"
    contact = " · ".join([
        f"{P['location']['city']}, {P['location']['country']}",
        f'<a href="mailto:{e(P["email"])}">{e(P["email"])}</a>',
        f'<a href="{e(SITE)}">{e(SITE.split("://")[1].rstrip("/"))}</a>',
    ] + [f'<a href="{e(l["url"])}">{e(l["url"].split("://")[1].replace("www.", "").rstrip("/"))}</a>' for l in P["links"]])

    edu = "\n".join(cv_entry(ed["degree"], ed["institution"], span(ed), ed["location"], details=ed["details"]) for ed in P["education"])
    exp = "\n".join(cv_entry(x["title"], x["organization"], span(x), x["location"], x["highlights"]) for x in P["experience"])
    teach = "\n".join(cv_entry(x["title"], x["organization"], span(x), x["location"], x["highlights"]) for x in P["teaching"])
    pubs = "\n".join(
        f"      <li>{authors_html(p)}. “{e(p['title'])}.”"
        f"{' <em>' + e(venue_line(p)) + '</em>.' if venue_line(p) else ''}"
        f"{' DOI ' + e(p['doi']) + '.' if p.get('doi') else ''} <strong>{e(p['status'])}</strong>.</li>" for p in PUBS)
    projs = "\n".join(
        f"      <li><strong>{e(p['title'])}</strong> ({e(p['period'])}). {e(p['summary'])}</li>"
        for p in PROJECTS if p["category"] == "engineering")
    skills = "\n".join(f"      <p><strong>{e(s['category'])}</strong><span>{e(', '.join(s['items']))}</span></p>" for s in P["skills"])
    langs = ", ".join(f"{l['language']} ({l['level'].lower()})" for l in P["languages"])

    body = f"""<div class="cv-bar">
  <a class="btn btn-secondary" href="{pre}">← Portfolio</a>
  <a class="btn btn-primary" href="{pre}{CV_PDF}" download>Download PDF</a>
</div>
<article class="sheet">
  <header>
    <h1>{e(P['name'])}</h1>
    <p class="role">{e(P['currentRole'])} · {e(P['headline'])}</p>
    <p class="contact">{contact}</p>
  </header>
  <section><h2>Summary</h2><p>{e(P['summary'])} {e(P['availability'])}.</p></section>
  <section><h2>Education</h2>
{edu}
  </section>
  <section><h2>Experience</h2>
{exp}
  </section>
  <section><h2>Publications</h2>
    <ol>
{pubs}
    </ol>
  </section>
  <section><h2>Teaching &amp; mentoring</h2>
{teach}
  </section>
  <section><h2>Selected projects</h2>
    <ol>
{projs}
    </ol>
    <p class="text-muted">Research projects with abstracts and figures are at {e(SITE)}#projects</p>
  </section>
  <section class="skills-cv"><h2>Skills</h2>
{skills}
      <p><strong>Languages</strong><span>{e(langs)}</span></p>
  </section>
</article>"""
    ld = {"@context": "https://schema.org", **person_ld()}
    return page(path="cv/", pre=pre, title=f"CV | {P['name']}",
                description=f"Curriculum vitae of {P['name']}, {P['currentRole']}, covering education, experience, publications and skills.",
                body=body, og_type="profile", ld=ld, extra_head=CV_CSS)


# ─── redirects, sitemap, robots, llms.txt ────────────────────────────────────

def redirect_stub(target):
    url = SITE + target
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved</title>
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={url}">
</head>
<body>
<p>This page has moved to <a href="{url}">{url}</a>.</p>
</body>
</html>
"""


def sitemap():
    urls = [("", "1.0"), ("cv/", "0.8")] + [(f"projects/{p['slug']}/", "0.7") for p in PROJECTS]
    rows = "\n".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY.isoformat()}</lastmod><priority>{pr}</priority></url>" for u, pr in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n'


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n"


def llms_txt():
    L = [f"# {P['name']}", "", f"> {P['currentRole']}. {P['summary']}", "",
         f"- Email: {P['email']}", f"- Website: {SITE}", f"- CV (HTML): {SITE}cv/", f"- CV (PDF): {SITE}{CV_PDF}"]
    L += [f"- {l['label']}: {l['url']}" for l in P["links"]]
    L += [f"- Structured data (JSON): {SITE}data/profile.json, {SITE}data/projects.json, {SITE}data/publications.json",
          f"- Location: {P['location']['city']}, {P['location']['country']}", "",
          "## At a glance",
          f"- Projects: {len(PROJECTS)}",
          f"- Publications: {len(PUBS)} ({sum(is_first_author(p) for p in PUBS)} first-author)",
          f"- Experience: {int(years_experience())}+ years (since {month(P['careerStart'])})",
          f"- Status: M.S. candidate in Robotics, graduating {month(P['education'][0]['end'])}",
          f"- Availability: {P['availability']}", "",
          "## Education"]
    L += [f"- {ed['degree']}, {ed['institution']}, {ed['location']}. {span(ed)}. " + ". ".join(ed["details"]) + "." for ed in P["education"]]
    for head, items in (("Experience", P["experience"]), ("Teaching & mentoring", P["teaching"])):
        L += ["", f"## {head}"]
        for x in items:
            L.append(f"- {x['title']}, {x['organization']}, {x['location']}. {span(x)}.")
            L += [f"  - {h}" for h in x["highlights"]]
    L += ["", "## Publications"]
    for p in PUBS:
        pos = p["authors"].index(P["name"]) + 1
        role = "First author" if pos == 1 else f"Author {pos} of {len(p['authors'])}"
        line = f"- {p['title']}. {', '.join(p['authors'])}. {venue_line(p) + '. ' if venue_line(p) else ''}{p['status']}. {role}."
        if p.get("doi"):
            line += f" DOI: {p['doi']}."
        if p.get("project"):
            line += f" Abstract: {SITE}projects/{p['project']}/"
        L.append(line)
    L += ["", "## Projects"]
    for p in PROJECTS:
        L.append(f"- {p['title']} ({p['category']}, {p['period']}; {p['role']}). {p['summary']} {SITE}projects/{p['slug']}/")
    L += ["", "## Skills"] + [f"- {s['category']}: {', '.join(s['items'])}" for s in P["skills"]]
    L.append("- Languages: " + ", ".join(f"{l['language']} ({l['level'].lower()})" for l in P["languages"]))
    return "\n".join(L) + "\n"


def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  {rel}")


def main():
    for p in PUBS:
        assert P["name"] in p["authors"], p["id"]
        assert not p.get("project") or p["project"] in PROJ_BY_SLUG, p["id"]
    for p in PROJECTS:
        assert not p.get("publication") or p["publication"] in PUB_BY_ID, p["slug"]
        assert (ROOT / f"assets/images/projects/{p['slug']}/cover.jpg").exists(), p["slug"]
        for f in p.get("figures", []):
            assert (ROOT / f["src"]).exists(), f["src"]

    print("Writing:")
    write("index.html", build_home())
    for i, proj in enumerate(PROJECTS):
        write(f"projects/{proj['slug']}/index.html", build_project(i, proj))
    write("cv/index.html", build_cv())
    for old, new in REDIRECTS.items():
        write(f"{old}/index.html", redirect_stub(new))
    write("sitemap.xml", sitemap())
    write("robots.txt", robots())
    write("llms.txt", llms_txt())


if __name__ == "__main__":
    main()
