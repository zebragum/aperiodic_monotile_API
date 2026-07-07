# Gumroad launch playbook — Aperiodic Monotile Generator

Use this to publish a **polished** Gumroad storefront without fighting Stripe for the same SKU twice.

## Strategy (what belongs where)

| Channel | Sell | Why |
|---------|------|-----|
| **Gumroad** | Blender Kit (one-time), optional Sample Pack | Discovery, Blender crowd, instant download, email list |
| **aperiodicgenerator.com** | API keys (Free / Solo / Pro) | Recurring billing, key minting, docs, job queue |

**Do not** sell duplicate “lifetime API keys” on Gumroad unless you automate fulfillment (manual keys burn time). Instead: Gumroad product **includes a discount code** for Solo lifetime on the site, or clear “Step 2: get your key at…” in `START_HERE.txt`.

---

## Product 1 (hero) — publish this first

### Display name
**Aperiodic Monotile Kit for Blender — Natural Non-Repeating Surfaces**

### URL slug
`spectre-monotile-blender-kit`

### Price (pick one launch tier)
- **$29** launch (feels premium, low support burden)
- **$39** after first 20 sales
- Optional **$49** “Pro” later when you add fill-selected-mesh

### Content files (upload one ZIP)
Build locally:

```powershell
cd spectre_patch_api\gumroad
.\build_gumroad_bundle.ps1
```

Upload: `dist/aperiodic-monotile-blender-kit.zip`

### Cover image (1280×720 or 3:2)
Use one of:
- Site hero poster: `site/assets/generator-video-poster.jpg`
- Export `site/assets/examples/circle-100u.svg` to PNG at 1280px wide
- Frame from `site/assets/generator-video.mp4` at 5s

Add short text overlay in Canva/Figma:
**“Stop obvious tile repetition in Blender”**

### Thumbnail (square)
Brand mark on dark background + “Blender” badge.

### Tags
Blender, spectre, monotile, aperiodic, procedural, 3D, environment, GLB, tiling, non-repeating

### Summary (Gumroad short description)
```
Stop obvious CG tiling. Generate aperiodic monotile floors and panels as GLB in Blender — ordered variation that reads more natural on camera.
```

### Description (paste into Gumroad — rich text)

Use the block in **PRODUCT_PAGE_COPY.md** (same folder).

### Settings checklist
- [ ] **Currency:** USD
- [ ] **Version:** 1.0.0 (bump when you ship add-on updates)
- [ ] **Email receipt:** ON — paste “What’s inside + link to START_HERE”
- [ ] **PDF stamp / watermark:** OFF
- [ ] **Rating:** ON after 10 happy buyers
- [ ] **Custom domain:** optional later (`yourname.gumroad.com`)
- [ ] **Cross-sell:** link to free demo on aperiodicgenerator.com
- [ ] **Affiliates:** 20% after product is stable

### Receipt email (paste)
```
Thanks for grabbing the Aperiodic Monotile Kit for Blender.

1. Download the ZIP from this page.
2. Read START_HERE.txt first.
3. Get your API key at https://aperiodicgenerator.com/docs.html#access
   (Free = PNG/JPG tests only; Solo = GLB production.)

If anything fails, reply to this email with your Blender version and a screenshot of the Monotile panel.

— Aperiodic Monotile Generator
```

---

## Product 2 (optional) — Fabrication Sample Pack

**Name:** Laser-Ready Aperiodic Monotile Samples (SVG + STL)  
**Price:** $12  
**ZIP:** `site/assets/samples/*` only + one-page “how to open in LightBurn” note  
**WHY:** “Test laser/CNC without subscribing first.”

---

## Profile page (Gumroad storefront)

**Bio one-liner:**
> Hosted aperiodic monotile geometry for Blender, fabrication, and code — non-repeating structure without hand-drawing every tile.

**Banner:** same as cover, wide crop.

**Pinned product:** Blender Kit.

**Also selling / More from me:**
- Free generator: aperiodicgenerator.com
- API for developers and laser workflows

---

## Launch week checklist

1. [ ] Build ZIP, install test on clean Blender 4.2
2. [ ] Run one free-key smoke test + one Solo GLB test
3. [ ] Publish Gumroad product (draft → preview → live)
4. [ ] Add Gumroad link to site footer + blender use-case page
5. [ ] One Twitter/Bluesky post: before/after “grid vs aperiodic” still
6. [ ] Blender Artists forum post (show GLB + add-on panel, link Gumroad + free demo)

---

## What “REAL nice” means on Gumroad

1. **One clear hero product** — not five confused SKUs on day one.
2. **Video or GIF** above the fold (15–30s: boundary pick → Generate → turntable).
3. **5–8 gallery images:** GLB viewport, wireframe, material randomize, circle vs hex mask, sample SVG in Inkscape.
4. **FAQ** answering: Do I need internet? (yes) Blender version? (4.0+) API cost? (free test / Solo for GLB) Studio or client work? (Pro plan on site)
5. **Refund policy** aligned with `site/refund.html` (link it).

---

## Discount code workflow (recommended)

On Stripe/site: create coupon `GUMROAD20` → 20% off Solo lifetime.  
Put code in Gumroad receipt + START_HERE.txt.  
Do **not** auto-generate API keys in Gumroad unless you build a webhook.
