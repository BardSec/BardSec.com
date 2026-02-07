# CLAUDE.md — BardSec.com Repository Guide

## Overview

BardSec.com is a static asset and marketing repository for **BardSec**, a cybersecurity-focused organization. This repository contains branding assets, product screenshots, and placeholder web content (privacy policies). There is no application code, build system, or runtime framework.

## Repository Structure

```
BardSec.com/
├── assets/              # Brand logos, marketing images, product thumbnails
│   ├── bardsec-logo.png # Primary brand logo
│   ├── favicon.png      # Browser favicon
│   ├── weblogo.png      # Web logo variant
│   └── ...              # Additional marketing/product images
├── filtertrace/         # FilterTrace product page assets
│   ├── privacy-policy.html
│   └── ss.png           # Product screenshot
├── recordkeeper/        # RecordKeeper product page assets
│   ├── privacy-policy.html
│   └── ss.png           # Product screenshot
├── temppad/             # TempPad product page assets
│   └── privacy-policy.html
└── CLAUDE.md            # This file
```

## Products / Services

- **FilterTrace** — Network/security filtering tool
- **RecordKeeper** — Record management system
- **TempPad** — Temporary notepad service
- **Zero Trust Given** — Zero Trust security concept/branding
- **K-12 Cyber Café** — Educational cybersecurity program
- **Red Team** — Penetration testing / red team services
- **Merchandise** — Branded physical products

## Technical Details

- **No build system** — No package.json, no bundler, no CI/CD pipeline
- **No testing framework** — No tests exist
- **No linting/formatting** — No ESLint, Prettier, or similar tools configured
- **No .gitignore** — None present; be careful not to commit sensitive or unnecessary files
- **Image format** — All images are PNG
- **Privacy policy pages** — HTML files exist as empty placeholders; content needs to be authored

## Conventions

- **File naming**: Lowercase, no spaces. Multi-word names use concatenation (e.g., `bardsec-logo.png`, `edtechirlthumb.png`).
- **Directory naming**: Lowercase product names as directory names (e.g., `filtertrace/`, `recordkeeper/`, `temppad/`).
- **Assets directory**: All shared brand/marketing images go in `assets/`.
- **Product directories**: Each product gets its own top-level directory containing its privacy policy and screenshot.

## Git Workflow

- **Default branch**: `main`
- **Commit style**: Short descriptive messages (historically "Add files via upload" or "Create <filename>")
- **No CI/CD**: Commits go directly to branches; no automated checks run

## Notes for AI Assistants

- This is a static asset repo — there is nothing to build, test, or lint.
- When adding new products, create a top-level directory with a `privacy-policy.html` and product screenshot (`ss.png`).
- Large image files (some are 6000x3000px / 24MB) are committed directly. Consider suggesting image optimization if the repo grows significantly.
- The privacy policy HTML files are currently empty placeholders and need real content.
