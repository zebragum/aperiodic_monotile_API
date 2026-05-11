# Production Checklist

A mechanical, top-to-bottom procedure for bringing the Spectre Patch API up in
production. Don't skip steps; each item has burned somebody before.

---

## 1. Provision

- [ ] **Compute**: 2 vCPU + 4 GB RAM is enough for API + worker per replica.
      The retention loop is the bottleneck; CPU helps more than RAM until you
      load n=8/n=9 cores in-process.
- [ ] **Disk**: budget for `data/` = atlas + jobs + DB. n=7 atlas alone is 50 MB;
      n=9 is ~3 GB. Each completed job writes 1–500 MB of artifacts depending on
      formats and SVG size. Set up a periodic cleanup job (see §7).
- [ ] **Network**: API listens on 8000, worker has no inbound port.
- [ ] **TLS**: terminate at a reverse proxy (Caddy, nginx, ALB). The container
      already trusts `--proxy-headers --forwarded-allow-ips '*'`.

## 2. Secrets

Generate two secrets and inject as env vars (NOT into the image):

- [ ] `SPECTRE_PATCH_API_SECRET` — 32-byte hex; signs all download URLs.
      `openssl rand -hex 32`
- [ ] `SPECTRE_PATCH_API_KEY_TIERS_JSON` — JSON object mapping client API key
      to server-side tier, for example:
      `{"free_xxx":"tier_free","day_xxx":"tier_day_pass","solo_xxx":"tier_solo","teams_xxx":"tier_teams"}`.
      Do not trust client-supplied `X-API-Tier`; the API ignores it in production.
- [ ] `SPECTRE_PATCH_REQUIRE_API_KEY=true` (default in `docker-compose.yml`).
- [ ] `SPECTRE_PATCH_ADMIN_TOKEN` — separate private token for admin-only lead
      export. Do not reuse customer API keys for this.
- [ ] Provision `support@aperiodic-monotile.com` or update all public policy
      pages to the real launch support inbox before enabling checkout.
- [ ] Copy the live Stripe values from local `.env` into Render secret env vars:
      `SPECTRE_PATCH_STRIPE_SECRET_KEY`, all five
      `SPECTRE_PATCH_STRIPE_PRICE_ID_*` values, and
      `SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET`.

If you forget the API secret, **all signed download URLs become forgeable** —
emergency-rotate by issuing a new secret and discarding signed URL TTLs.

## 3. Atlas seeding

The API works without an atlas (live substitution at request time), but
production should ship at least n=5..n=7 cores or every request pays the
substitution cost.

- [ ] Build n=5..n=7 on any laptop:
      ```bash
      python -m spectre_patch.atlas.cli build 5 --out data/atlas
      python -m spectre_patch.atlas.cli build 6 --out data/atlas
      python -m spectre_patch.atlas.cli build 7 --out data/atlas --raster 1024
      ```
- [ ] (Optional) Build n=8/n=9/n=10 from `notebooks/build_deep_atlas_colab.ipynb`
      and `unzip` the artifact into the deployment's `data/atlas/`.
- [ ] Verify: `python -m spectre_patch.atlas.cli list --out data/atlas` should
      list every depth you intend to support.
- [ ] After seeding, restart the API container so the lifespan reload picks up
      the new manifest.

## 4. Database

The DB is a single-file SQLite with WAL mode (`monotile.db`, `*.db-wal`,
`*.db-shm`). The schema migrates itself.

- [ ] **Backups**: snapshot `data/` every hour (`rsync` or your snapshot
      provider). The WAL file must be included.
- [ ] **Concurrency**: WAL mode + `busy_timeout=5000ms` lets the API and worker
      share writes. Add more workers via `WORKER_REPLICAS=N` in `docker-compose.yml`.
- [ ] **Resilience**: if the worker dies mid-job the next worker startup
      re-queues anything stuck in `running` for more than `--requeue-after-sec`
      (default: 2h).

## 5. Container runtime

```bash
export SPECTRE_PATCH_API_SECRET=$(openssl rand -hex 32)
export FREE_API_KEY=free_$(openssl rand -hex 16)
export DAY_PASS_API_KEY=day_$(openssl rand -hex 16)
export SOLO_API_KEY=solo_$(openssl rand -hex 16)
export TEAMS_API_KEY=teams_$(openssl rand -hex 16)
export SPECTRE_PATCH_API_KEY_TIERS_JSON="{\"$FREE_API_KEY\":\"tier_free\",\"$DAY_PASS_API_KEY\":\"tier_day_pass\",\"$SOLO_API_KEY\":\"tier_solo\",\"$TEAMS_API_KEY\":\"tier_teams\"}"
export SPECTRE_PATCH_CORS_ALLOW_ORIGINS=https://your-frontend.example.com
export WORKER_REPLICAS=2
docker compose up -d --build
```

- [ ] Verify health: `curl -fsS http://localhost:8000/healthz` → 200
- [ ] Verify readiness: `curl -fsS http://localhost:8000/readyz` → 200
- [ ] Verify capabilities: `curl http://localhost:8000/v1/capabilities -H "X-API-Key: <key>"`
- [ ] After Render deploy, run the non-Stripe live smoke test:
      ```bash
      SPECTRE_PATCH_SMOKE_API_BASE=https://aperiodic-monotile-api.onrender.com \
      SPECTRE_PATCH_SMOKE_API_KEY=<free-or-paid-key> \
      python scripts/live_smoke_api.py
      ```
- [ ] After Stripe env vars are present in Render, start one live Checkout
      session from the pricing page and verify Stripe redirects to
      `/docs.html?checkout=success&session_id=...#access`.
- [ ] Smoke a real job:
      ```bash
      curl -X POST http://localhost:8000/v1/patch \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $FREE_API_KEY" \
        -H "Idempotency-Key: smoke-001" \
        -d '{
          "formats": ["png", "jpg"],
          "png_width_px": 512,
          "png_height_px": 512,
          "jpg_width_px": 512,
          "jpg_height_px": 512,
          "mask": {"type": "circle", "radius": 12}
        }'
      ```
      Poll `GET /v1/jobs/{id}` until `status: completed`, then bundle URLs:
      ```bash
      curl http://localhost:8000/v1/jobs/<id>/urls -H "X-API-Key: $key"
      ```

### Render deployment notes

- [ ] `render.yaml` should keep `SPECTRE_PATCH_LOG_LEVEL=info`; Uvicorn rejects
      uppercase log levels.
- [ ] Launch architecture decision: use one Render Docker web service with a
      64 GB persistent disk and run `/app/entrypoint.sh api-worker`. This starts
      Uvicorn and `spectre-patch-worker` as separate processes in the same
      container so they share SQLite, the atlas, and generated artifacts on the
      attached disk.
- [ ] Keep `SPECTRE_PATCH_RUN_JOBS_IN_PROCESS=false` in Render. In-process jobs
      are only for local development and can be lost when the API restarts.
- [ ] Keep `SPECTRE_PATCH_MAX_OUTPUT_BYTES_SOFT=32212254719` unless the Render
      disk is expanded. That preserves the 30 GB product ceiling while leaving
      room for the atlas, SQLite WAL files, and short-lived job metadata.
- [ ] Do not split Render API and worker into two services while using SQLite
      and local artifacts; Render disks are attached to one service. If traffic
      outgrows this launch architecture, migrate job state to Postgres and
      artifacts to S3/R2 before splitting services.
- [ ] Keep `SPECTRE_PATCH_API_KEY_TIERS_JSON` only in Render environment
      variables. Do not commit real free, Day Pass, Solo, or Teams keys.
- [ ] Set `SPECTRE_PATCH_ADMIN_TOKEN` as a secret value if the launch-list form
      is enabled; use it with `GET /v1/admin/leads?fmt=csv`.
- [ ] Before pointing a custom web domain at Render, verify `/healthz`,
      `/readyz`, `/v1/capabilities`, and one signed artifact download over the
      Render hostname. Repeat after DNS/TLS is live on the domain.
- [ ] Configure Render health checks against `/healthz`. Use `/readyz` for
      deploy smoke checks because it verifies DB, storage, and atlas count.

## 6. Observability

The API logs **structured JSON** to stdout with request-id, path, status,
elapsed, tier. Pipe to your collector (Loki, CloudWatch, Datadog Logs).

- [ ] Add a JSON log parser to your collector and pin alerts on:
      - `unhandled request error` (any occurrence → page)
      - `worker` log "stale running" warnings (low rate is OK; spike means
        worker keeps crashing mid-job)
      - `mark_failed` rate (track per-tier)
- [ ] `/metrics` returns queue depth + atlas core count + uptime. Scrape with
      a sidecar that converts to Prometheus, or read it from a healthcheck cron.
- [ ] Track download-URL signature mismatches (403s on `/v1/downloads/*`) —
      consistent failures are a sign of clock skew or secret rotation that
      didn't propagate.

## 7. Lifecycle / GC

The job table grows unboundedly; artifacts grow even faster.

- [ ] Daily cron: delete terminal jobs and artifacts older than the launch
      retention window. Start with a dry run:
      ```bash
      spectre-patch-gc --older-than-hours 24 --dry-run
      spectre-patch-gc --older-than-hours 24
      ```
- [ ] On Render, run the same command from a cron job or manual shell until a
      managed cron service is configured. The command uses
      `SPECTRE_PATCH_DB_PATH` and `SPECTRE_PATCH_STORAGE_DIR` by default.
- [ ] Per-tier retention overrides if your billing SKU promises longer
      artifact lifetimes — set `download_ttl_seconds` accordingly per request.

## 8. Rate limiting / abuse

- [ ] `SPECTRE_PATCH_RATE_LIMIT_POST_PATCH=30/minute` is per-client-IP. Tune
      with the slowapi grammar (`60/minute`, `1000/day`, etc.).
- [ ] In production, fronting the API with a CDN/WAF that does coarse-grained
      throttling is advisable; slowapi is a fine inner layer but not a DDoS
      shield.
- [ ] Per-tier overrides are resolved server-side from
      `SPECTRE_PATCH_API_KEY_TIERS_JSON`; free users cannot self-upgrade with
      `X-API-Tier`.

## 9. Upgrade procedure

The atlas format and the substitution rules both have versions:

- `ATLAS_FORMAT_VERSION` — bump if you change the npz layout. Existing cores
  must be rebuilt; old ones are rejected at load.
- `PATCH_ENGINE_SEMVER` — bump if you change substitution rules or the prototile.
  This invalidates `stable_tile_id` for the same DFS path, so it's effectively
  an ABI break for downstream consumers (Blender drivers etc.).

Roll forward: build new cores → deploy new image → restart API. Roll back: keep
the previous image's atlas dir and `git revert` the `PATCH_ENGINE_SEMVER` bump.

## 10. Security review

- [ ] Filename traversal: the download endpoint already rejects `/`, `\`,
      and `..`. Don't loosen it.
- [ ] `svg_fill` / `svg_stroke` are checked for `< > " ' \n` so the SVG can't
      be repurposed for XSS even if served from your domain. Still, prefer
      serving via the signed URL endpoint with `Content-Disposition: attachment`
      for unknown integrators.
- [ ] **Path traversal in artifact dirs**: storage_dir resolution is checked
      against the artifact path's resolved prefix — keep it that way.
- [ ] `pip-audit` on every release: `pip-audit -r <requirements.txt>` (the
      `dev` extras include it).
- [ ] Rotate any setup keys that were pasted into local shells, chat, or shared
      terminals. Render API keys and public API keys should live only in the
      provider dashboard or a secret manager.
- [ ] Keep generated test artifacts out of git. `.gitignore` excludes atlas
      archives, local DBs, and ad-hoc `api_*` visual SVG/PNG files.

## 11. CI / release gate

- [ ] GitHub Actions should run `python -m pytest -q` on every push and pull
      request.
- [ ] Before deploying, run the local full test suite and one live smoke test
      against the Render service.
- [ ] For release candidates that touch dependencies, run `pip-audit` locally
      or in a scheduled CI workflow.
- [ ] Confirm the public site includes Terms, Privacy, Refund, Contact, and
      Attribution pages before taking payment.

## 12. Disaster recovery

- [ ] Document the steps for rebuilding `data/atlas/` from the Colab notebook;
      n=5..n=7 takes < 10 minutes total.
- [ ] Document the secret-rotation flow (new env var → restart API + worker;
      old signed URLs become invalid, that's the intended behaviour).
- [ ] Store an off-host backup of `data/` so you can restore the DB + atlas
      after a host loss.

## 13. Done?

If every box is ticked, the API can serve launch traffic with one unattended
Render service running API + worker processes, no database other than SQLite,
and zero external dependencies beyond the attached filesystem.
