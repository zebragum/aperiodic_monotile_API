# Launch-time breakage risks

A short list of failure modes that are easy to overlook, with current status
and follow-up notes. The intent is that anybody — including a future you —
can read this and know what's already been mitigated and what's left.

| Risk | Status | Notes |
|------|--------|-------|
| Worker dies mid-job and never restarts | Mitigated | `entrypoint.sh api-worker` now respawns `spectre-patch-worker` in a `while true` loop. API stays up. |
| Stripe webhook silently mints permanent Solo keys | Mitigated | `/v1/billing/webhook` and `/v1/billing/claim-key` refuse to mint when `metadata.tier` is missing and the plan slug doesn't match a known SKU. Day Pass falls back to canonical TTL if `key_ttl_seconds` is missing. |
| Stripe error responses leak product/customer data | Mitigated | `_stripe_post` / `_stripe_get` log full Stripe body, return a generic 502 detail. |
| Unhandled exception leaks stack/trace to caller | Mitigated | Global `Exception` handler returns the standard error envelope with only `request_id` + support link; full traceback only lands in the structured log. |
| Customers can't find their request when something fails | Mitigated | `X-Request-ID` is exposed on every response; the docs site bug-report widget auto-attaches the last seen request id; error envelope includes the same id and a `support` URL. |
| Bug reports have nowhere to go | Mitigated | `POST /v1/bug-reports` persists to SQLite. `GET /v1/admin/bug-reports?fmt=csv` exports under the admin token. |
| Artifact disk fills up | Mitigated | `spectre-patch-gc` runs inside the `api-worker` container every `SPECTRE_PATCH_GC_INTERVAL_SEC` seconds (default 6h), deleting terminal jobs older than `SPECTRE_PATCH_GC_OLDER_THAN_HOURS` (default 24h). Render disks attach to one service so an external cron cannot see this disk. |
| Atlas missing from disk after a fresh Render deploy | Mitigated | `SPECTRE_PATCH_BOOTSTRAP_ATLAS=true` in `render.yaml` causes `bootstrap_atlas.py` to download from `SPECTRE_PATCH_ATLAS_RELEASE_URL` on startup. Verify cores exist via `GET /v1/capabilities` after deploy. |
| SQLite write contention | Mitigated | WAL mode + 5s busy_timeout. `UVICORN_WORKERS=1`, single API process. |
| Signed URL forgery if API secret leaks | Documented | Rotate `SPECTRE_PATCH_API_SECRET` in Render — old URLs become invalid by design. |
| Free tier customer requests SVG | Mitigated | `POST /v1/patch` raises 422 with the new error envelope; worker double-checks via `FREE_TIER_RASTER_FORMATS`. |
| Schema accepts old `coverage_half_extent`/`retention`/`center` knobs | Mitigated | Pydantic schema rejects them with 422. Public docs and Blender plugin no longer mention them. |
| OPTIONS preflight to a non-listed origin | Documented | `SPECTRE_PATCH_CORS_ALLOW_ORIGINS` is a comma-separated list — add custom domains there before pointing DNS. |
| Idempotency-Key omitted on retries | Documented | Without an idempotency key, retried `POST /v1/patch` creates duplicate jobs. Docs already explain it; the demo/Blender plugin set one automatically. |
| Stripe webhook delivery replays | Mitigated | Signature timestamp must be within 300 seconds; replays older than that are rejected. `find_api_key_by_checkout_session` makes the mint idempotent. |
| Render dashboard drift overrides `render.yaml` | Mitigated | Render reads `render.yaml` only on first deploy. After that, dashboard settings (dockerCommand, plan, disk size, env vars) take precedence and `render.yaml` becomes documentation. **Verify before launch with `GET /v1/services/{id}` — confirm `dockerCommand` ends with `api-worker`, `plan: standard`, and `disk.sizeGB: 64`.** This bit us once: the service was provisioned with `dockerCommand: ... api` and the worker never ran. |
| Backups | Open | Render disk snapshots aren't automated yet. For launch, a manual snapshot before deploy is the minimum. Long-term: scheduled `pg_dump`-equivalent or move to Postgres. |
| Email deliverability | Open | `zach@shopcloudburst.com` must actually receive mail before checkout receipts go to customers; verify with a test purchase. |
| Logs aren't aggregated | Open | Render captures stdout JSON. A log sink (Datadog/Logtail/Sentry) is recommended before paid traffic so 5xx spikes alert. |

## Operating notes

- Every 5xx or 4xx now returns an envelope shaped like:

```json
{
  "error": {
    "code": "invalid_request",
    "status": 422,
    "message": "...",
    "request_id": "1e9d...",
    "support": "https://aperiodic-monotile-site.onrender.com/contact.html?rid=1e9d..."
  }
}
```

  The `message` is either a string or a structured Pydantic error list — never a server path, traceback, or SQL.

- The `X-Request-ID` response header carries the same id, and clients can also pass an inbound `X-Request-ID` to correlate spans they own with our logs.

- `POST /v1/bug-reports` is unauthenticated and rate-limited so frustrated users can always file something. Spam is contained by the 8000-character cap and IP-hash bookkeeping.

- The in-container GC loop never deletes queued/running jobs, only terminal rows older than the retention window.
