# Dwiweka Naratama | Portfolio

Personal portfolio in robotics and AI, covering 3D scene understanding, navigation and real-robot deployment.

**Live:** https://dwiwekan.github.io/portfolio/

## How it works

All content lives in `data/*.json`. `scripts/build.py` turns it into plain static HTML, so
every word is in the page source: no JavaScript rendering, which keeps the site readable by
ATS parsers, search engines and AI agents. Each page gets a proper `<head>` (title,
description, canonical URL, Open Graph) and schema.org JSON-LD (Person, ProfilePage,
ScholarlyArticle).

**Edit the JSON, then rebuild. Don't edit the generated HTML by hand.**

```
.
├── data/
│   ├── profile.json          # Name, summary, experience, teaching, education, skills
│   ├── projects.json         # One entry per project card / project page
│   └── publications.json     # Papers; each links to a project by slug
├── scripts/
│   ├── build.py              # Generates every page below (Python 3, standard library + optional Pillow)
│   └── optimize_images.py    # Resize/compress a figure for the web
├── index.html                # generated · home          → /portfolio/
├── projects/<slug>/          # generated · project pages → /portfolio/projects/<slug>/
├── cv/                       # generated · HTML CV       → /portfolio/cv/
├── print/, projects/{scene-graph,map-prediction,attention-nav}/   # generated redirects from old URLs
├── sitemap.xml, robots.txt, llms.txt                             # generated
├── assets/
│   ├── design-system/        # "Broadsheet" tokens and component classes (styles.css)
│   ├── css/site.css          # Site layout
│   ├── images/profile/       # portrait.jpg
│   ├── images/projects/<slug>/   # cover.jpg (card + social preview) and figures (.webp)
│   ├── videos/               # Compressed MP4s
│   └── documents/            # Ida-Bagus-Dwiweka-Naratama-CV.pdf
└── private/                  # gitignored: original uploads, paper PDFs, source CV — never published
```

## Build and preview

```bash
python3 scripts/build.py
python3 -m http.server 8000 --directory ..   # then open http://localhost:8000/portfolio/
```

Regenerate the PDF CV after changing profile or publication data (the server must be running):

```bash
google-chrome --headless=new --no-pdf-header-footer \
  --print-to-pdf=assets/documents/Ida-Bagus-Dwiweka-Naratama-CV.pdf \
  http://localhost:8000/portfolio/cv/
```

## Adding a project

1. Optimise its images into `assets/images/projects/<slug>/`:
   ```bash
   python3 scripts/optimize_images.py private/uploads/fig.png assets/images/projects/<slug>/method.webp
   python3 scripts/optimize_images.py private/uploads/fig.png assets/images/projects/<slug>/cover.jpg --width 1200
   ```
   `cover.jpg` is required (card thumbnail and social preview).
2. Add an entry to `data/projects.json` (`category` is `research` or `engineering`; add
   `"coverFit": "cover"` for photos that should fill the card).
3. If it's a paper, add it to `data/publications.json` and set `publication` / `project` to link the two.
4. Run `python3 scripts/build.py`. It checks that every referenced image exists.

Papers themselves (PDF, HWP, DOCX) stay in `private/`; the site only shows abstracts and figures.

## Deploy

GitHub Pages serves the `main` branch root. Push to `main` and the site updates in about a minute.
