# Commercialization Plan

> **Live pricing (site + API):** Free · Solo ($10/mo or $79 lifetime, 40k tiles/job) · Pro ($99/mo or $999 lifetime, 400k tiles/job). Internal paid-studio tier id remains `tier_teams`. Older Teams/Commercial figures below are historical notes.

This project makes money by selling convenient, reliable access to generated
Spectre monotile geometry. The API is the product; plugins and the website are
the storefront.

## Recommended Launch Funnel

1. **Public static website**
   - Preloaded examples for cheap public demos.
   - SEO-focused pages for aperiodic monotile, Spectre tile, Blender tiling,
     SVG tiling, CAD pattern generator, and fabrication use cases.
   - Clear CTA for API access.
   - Lead capture through `POST /v1/leads`, with private CSV/JSON export through
     `GET /v1/admin/leads` once `SPECTRE_PATCH_ADMIN_TOKEN` is configured.

2. **Free API tier**
   - Small preview patches only.
   - Raster image preview exports only (JPG/PNG), capped by free-tier rules.
   - Low rate limits.
   - Short artifact retention.
   - Good enough for developers and designers to verify the value.

3. **Paid Day Pass, Solo & Teams SKUs (`tier_day_pass` / `tier_solo` / `tier_teams`)**
   - Larger masks and higher tile counts.
   - Full exporters: SVG, CSV, JSON, STL, glTF, instance manifests.
   - Operational quality: reliability, fidelity, tooling, integrations, docs.
   - Longer-lived artifacts + commercial suitability once keys are contracted.

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
5. The API verifies the paid session with Stripe and creates API keys persisted in SQLite mapped to tiers from Checkout metadata (`tier_day_pass`, `tier_solo`, `tier_teams`). Day Pass keys get a 24-hour expiry.
6. Stripe webhook support is available for automatic provisioning/recovery.

The current Render deployment supports both the original environment-variable
key map and persistent database-backed keys. Manual launch can keep using
`SPECTRE_PATCH_API_KEY_TIERS_JSON`; Stripe launch should use the DB-backed flow.

Request body `{ "email": "...", "plan": "day_pass" | "solo_monthly" | "solo_yearly" | "teams_monthly" | "teams_yearly" }`.
Omitting `plan` defaults to Solo monthly (`solo_monthly`).

Required Stripe env vars:

- `SPECTRE_PATCH_STRIPE_SECRET_KEY`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_MONTHLY`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_YEARLY`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_MONTHLY`
- `SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_YEARLY`
- `SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET` (recommended for webhook recovery)
- `SPECTRE_PATCH_PUBLIC_SITE_URL`

Legacy compatibility: `SPECTRE_PATCH_STRIPE_PRICE_ID_STUDIO` may mirror Solo
monthly for older deployed images, but the public launch tiers are Day Pass,
Solo, and Teams.

Launch Stripe products/prices use stable lookup keys so setup can be rerun
without creating duplicate prices:

- `aperiodic_monotile_day_pass_5_usd` → Day Pass, $5 one-time payment.
- `aperiodic_monotile_solo_monthly_12_usd` → Solo, $12 monthly subscription.
- `aperiodic_monotile_solo_yearly_120_usd` → Solo, $120 yearly subscription.
- `aperiodic_monotile_teams_monthly_99_usd` → Teams, $99 monthly subscription.
- `aperiodic_monotile_teams_yearly_999_usd` → Teams, $999 yearly subscription.

Webhook endpoint:

- URL: `https://aperiodic-monotile-api.onrender.com/v1/billing/webhook`
- Event: `checkout.session.completed`
- Secret: store as `SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET`.

## Minimal Pricing Hypothesis

- **Free**: small preview patches, capped raster previews (`jpg/png`), public demos.
- **Day Pass**: $5/day — one-time checkout, 24-hour generated API key.
- **Solo**: $12/mo or $120/yr — freelancer / lone technical artist path.
- **Teams**: $99/mo or $999/yr — studio seats & onboarding headroom (same SKU limits today until product differentiates quotas).

## What Not To Do First

- Do not let anonymous users generate unlimited live patches.
- Do not promise impossible "view but not downloadable" protection for SVGs.
- Do not build a full account dashboard before validating paid interest.
- Do not make the Blender plugin perfect before showing the click-to-geometry
  demo.

## Launch Checklist

- [ ] Static site live.
- [ ] API live with free and paid keys.
- [ ] `SPECTRE_PATCH_ADMIN_TOKEN` configured so launch leads can be exported.
- [ ] One public demo video or animated screen capture.
- [ ] Blender add-on demo can request and import at least SVG output.
- [ ] Stripe Checkout product created.
- [ ] Paid-key fulfillment verified through Stripe Checkout claim flow.
- [ ] Domain connected and verified in Google Search Console.
