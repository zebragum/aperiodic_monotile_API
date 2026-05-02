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

1. Landing page sends user to Stripe Checkout.
2. Stripe webhook receives `checkout.session.completed`.
3. Webhook creates or activates an API key.
4. API key is inserted into `SPECTRE_PATCH_API_KEY_TIERS_JSON` storage or a
   future database-backed key table.
5. Customer receives a welcome email with docs and examples.

The current Render deployment stores API key tier mapping in an environment
variable. That is good for manual launch. For self-serve paid signup, replace it
with a persistent API key table.

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
