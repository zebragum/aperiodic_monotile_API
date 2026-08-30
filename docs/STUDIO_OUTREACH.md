# Studio outreach playbook

Use when SEO traffic is curiosity, not conversion. Goal: **10 conversations with environment artists / TDs**, not mass email.

## ICP (who actually pays)

| Segment | Pain | Offer |
|---------|------|-------|
| Archviz (10–50 person) | Floor repetition in walkthroughs | Floor pack + Pro trial |
| Indie game env art | Tileable textures look fake in third-person | Sci-fi panel + Blender kit |
| Fabrication shop | Unique lattice for client install | Laser screen pack |
| Tools TD at mid-size studio | Needs pipeline, not a toy | Site license + API |

Skip: pure mathematicians, Wikipedia tourists, crypto/NFT spam.

## Channels (in order)

1. **Direct email** — art directors at studios that ship visible floors (archviz reels on Vimeo, game env art on ArtStation).
2. **Blender Art / Poly Haven Discord** — one helpful post + link to digital packs, not spam.
3. **Gumroad discover** — tags: Blender, archviz, procedural, environment.
4. **LinkedIn** — short reel: square grid vs monotile floor, 20 seconds.
5. **Existing wiki backlinks** — email authors of papers in bibliography who use Hat-family geometry in graphics.

## Email template A (environment artist)

Subject: Non-repeating floor plate for [Project / reel]

Hi [Name],

I noticed [specific floor / panel / lattice in your reel or post]. We build production SVG/STL/GLB from the Spectre aperiodic monotile — same theorem as the 2023 Hat tile, but oriented for archviz and game floors.

I can send a free sample pack (3 floor plates + Blender import) if you want to drop one into a test scene. No subscription required for the files.

If your team needs custom sizes or hundreds of variants, we also run a hosted API (Pro tier, 400k tiles/job).

Worth a look?

[Your name]  
https://untiling.com/studio.html

## Email template B (tools TD)

Subject: Instance JSON + GLB pipeline for aperiodic tiling

Hi [Name],

Untiling exposes Tile(1,1) patches via REST with `instance_json`, GLB, and STL exports — meant for DCC pipelines rather than one-off demos.

Happy to share OpenAPI docs and a 15-min integration call if you're evaluating non-periodic ground meshes for [engine].

https://aperiodicgenerator.com/docs.html

## Follow-up (day 5)

Subject: Re: sample pack

Quick bump — I attached nothing yet because I wanted to match your typical plate size. If you reply with rough dimensions (meters or Blender units), I'll send the closest pack from our catalog.

## Metrics to track

Run weekly:

```powershell
cd spectre_patch_api\scripts
python fetch_analytics.py 30
```

Watch: `checkout_start`, `key_claim`, `first_successful_job`, lead count from `GET /v1/admin/leads?fmt=csv`.

## Do not

- Give unlimited free SVG via the public site (removed from `/assets/examples/`).
- Compete with Gumroad on the same SKU as Stripe API without fulfillment automation.
- Lead with "einstein problem" math — lead with **visible repetition in camera**.
