# Commercialization Plan

This project makes money by selling convenient, reliable access to generated
Spectre monotile geometry. The API is the product; plugins and the website are
the storefront.

## Recommended Launch Funnel

1. **Public static website**
   - Preloaded examples for cheap public demos.
   - SEO-focused pages for aperiodic monotile, Spectre tile, Blender tiling,
     SVG tiling, CAD pattern generator, and fabrication use cases.
   - Clear CTA for API access.

2. **Free API tier**
   - Small SVG previews.
   - Low rate limits.
   - Short artifact retention.
   - Good enough for developers and designers to verify the value.

3. **Paid Studio tier**
   - Larger masks and higher tile counts.
   - SVG, CSV, JSON, STL, glTF, and instance manifests.
   - Batch jobs.
   - Longer artifact retention.
   - Commercial usage rights and priority queue.

4. **Plugin-led demos**
   - Blender add-on first because it makes the practical value obvious.
   - Adobe/Illustrator workflow second because SVG is already a strong path.

## Stripe Integration Shape

Do not put Stripe secrets in the static site. The payment flow needs a tiny
backend endpoint or serverless function:

1. Landing page sends user to `POST /v1/billing/checkout`.
2. API creates a Stripe Checkout session.
3. Stripe redirects back to `docs.html?session_id={CHECKOUT_SESSION_ID}`.
4. The docs page calls `POST /v1/billing/claim-key`.
5. The API verifies the paid session with Stripe and creates a persistent
   `tier_pro` API key in SQLite.
6. Stripe webhook support is available for automatic provisioning/recovery.

The current Render deployment supports both the original environment-variable
key map and persistent database-backed keys. Manual launch can keep using
`SPECTRE_PATCH_API_KEY_TIERS_JSON`; Stripe launch should use the DB-backed flow.

Required Stripe env vars:

- `SPECTRE_PATCH_STRIPE_SECRET_KEY`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_STUDIO`
- `SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET` (recommended for webhook recovery)
- `SPECTRE_PATCH_PUBLIC_SITE_URL`

## Minimal Pricing Hypothesis

- **Free**: small previews, public examples, low quota.
- **Studio**: monthly paid access for designers, Blender users, and small shops.
- **Enterprise / Research**: custom limits, support, private atlas builds, and
  integration help.

## What Not To Do First

- Do not let anonymous users generate unlimited live patches.
- Do not promise impossible "view but not downloadable" protection for SVGs.
- Do not build a full account dashboard before validating paid interest.
- Do not make the Blender plugin perfect before showing the click-to-geometry
  demo.

## Launch Checklist

- [ ] Static site live.
- [ ] API live with free and paid keys.
- [ ] One public demo video or animated screen capture.
- [ ] Blender add-on demo can request and import at least SVG output.
- [ ] Stripe Checkout product created.
- [ ] Manual paid-key fulfillment documented.
- [ ] Domain connected and verified in Google Search Console.
