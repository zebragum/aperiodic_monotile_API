# Aperiodic Monotile API Website

Static marketing and documentation site for the Aperiodic Monotile API.

## What This Demo Does

- Shows pre-generated, view-only Spectre tiling examples.
- Avoids calling the live API on every visitor interaction, which keeps the free
  public demo cheap to host.
- Explains use cases, pricing direction, API request shape, and signed-download
  flow.

## Cost Notes

A public live generator can become expensive if every slider movement enqueues
API jobs. The recommended first launch is:

1. Static site + preloaded examples for anonymous visitors.
2. Authenticated API keys for downloadable/custom geometry.
3. Optional "Generate live preview" later, guarded by rate limits, CAPTCHA, and
   a low free quota.

## Local Preview

Open `index.html` in a browser, or serve the folder with any static server:

```bash
python -m http.server 8080
```

## Deployment

This folder can be deployed to Netlify, Vercel, Cloudflare Pages, GitHub Pages,
or any static host. Once the domain is known, update:

- `index.html` canonical URL
- Open Graph URL
- `robots.txt` sitemap URL
- `sitemap.xml` URLs
- CTA email address

Initial Render target:

- Site: `https://aperiodicgenerator.com`
- API: `https://api.aperiodicgenerator.com`
