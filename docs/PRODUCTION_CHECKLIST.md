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
- [ ] `SPECTRE_PATCH_VALID_API_KEYS` — comma-separated list of client API keys.
      One key per integrator. Rotate per-key.
- [ ] `SPECTRE_PATCH_REQUIRE_API_KEY=true` (default in `docker-compose.yml`).

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
export SPECTRE_PATCH_VALID_API_KEYS=$(uuidgen)
export SPECTRE_PATCH_CORS_ALLOW_ORIGINS=https://your-frontend.example.com
export WORKER_REPLICAS=2
docker compose up -d --build
```

- [ ] Verify health: `curl -fsS http://localhost:8000/healthz` → 200
- [ ] Verify readiness: `curl -fsS http://localhost:8000/readyz` → 200
- [ ] Verify capabilities: `curl http://localhost:8000/v1/capabilities -H "X-API-Key: <key>"`
- [ ] Smoke a real job:
      ```bash
      curl -X POST http://localhost:8000/v1/patch \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $SPECTRE_PATCH_VALID_API_KEYS" \
        -H "Idempotency-Key: smoke-001" \
        -d '{
          "tile_family": "spectre_tile_1_1",
          "scale": 1.0, "rotation_deg": 0.0,
          "coverage_half_extent": 12,
          "formats": ["svg", "csv"],
          "retention": "centroid",
          "mask": {"type": "circle", "center": [0,0], "radius": 12}
        }'
      ```
      Poll `GET /v1/jobs/{id}` until `status: completed`, then bundle URLs:
      ```bash
      curl http://localhost:8000/v1/jobs/<id>/urls -H "X-API-Key: $key"
      ```

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

- [ ] Daily cron: delete completed jobs older than `LimitsSettings.job_gc_hours`
      (default 24h). Skeleton:
      ```bash
      sqlite3 data/monotile.db <<SQL
      DELETE FROM patch_jobs
      WHERE finished_at IS NOT NULL
        AND finished_at < strftime('%s', 'now', '-1 day');
      SQL
      find data/jobs -mindepth 1 -maxdepth 1 -type d -mtime +1 -exec rm -rf {} +
      ```
- [ ] Per-tier retention overrides if your billing SKU promises longer
      artifact lifetimes — set `download_ttl_seconds` accordingly per request.

## 8. Rate limiting / abuse

- [ ] `SPECTRE_PATCH_RATE_LIMIT_POST_PATCH=30/minute` is per-client-IP. Tune
      with the slowapi grammar (`60/minute`, `1000/day`, etc.).
- [ ] In production, fronting the API with a CDN/WAF that does coarse-grained
      throttling is advisable; slowapi is a fine inner layer but not a DDoS
      shield.
- [ ] Per-tier overrides: read `request.state.monotile_tier` in custom
      middleware and dispatch tier-specific limiters.

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

## 11. Disaster recovery

- [ ] Document the steps for rebuilding `data/atlas/` from the Colab notebook;
      n=5..n=7 takes < 10 minutes total.
- [ ] Document the secret-rotation flow (new env var → restart API + worker;
      old signed URLs become invalid, that's the intended behaviour).
- [ ] Store an off-host backup of `data/` so you can restore the DB + atlas
      after a host loss.

## 12. Done?

If every box is ticked, the API can serve production traffic with one
unattended replica each of API + worker, no database other than SQLite, and
zero external dependencies beyond the host filesystem.
