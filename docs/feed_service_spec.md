# Feed Service — Cloud Run Specification

**Status:** Draft v1
**Owner:** Regulatory Intelligence
**Last updated:** 2026-04-22

---

## 1. Purpose

A standalone service that polls registered RSS/Atom feeds, stores each
published entry as a structured document, and exposes a REST API for
registering feeds (tagged with a topic at registration time) and
retrieving entries filterable by `topic` and `date`.

The service is intentionally **dumb**: it knows nothing about feed
discovery, editorial filtering, or summarization. Those concerns live
upstream in the Regulatory Intelligence App. This keeps the Feed
Service small, fast, cheap, and reusable by future consumers.

---

## 2. Scope

**In scope**
- Accept feed registrations (`feed_url`, `topic`, optional metadata).
- Poll all registered feeds on a fixed schedule.
- Parse entries with `feedparser`, deduplicate, persist.
- Serve entries via REST with `topic` + date-range filtering.
- HTTP-etiquette conditional polling (ETag / Last-Modified).
- Basic auth (API key) for write endpoints; read endpoints behind same key.

**Out of scope**
- Feed discovery (OPML, autodiscovery, Feedly, RSS.app, ScrapeGraphAI).
- Summarization, classification, editorial review.
- A UI. Consumers talk only via REST.
- Multi-tenant isolation. Single-tenant in v1.

---

## 3. Data model

### 3.1 `feeds` collection

| Field              | Type     | Notes                                          |
|--------------------|----------|------------------------------------------------|
| `id`               | string   | ULID, primary key                              |
| `feed_url`         | string   | Canonical feed URL (RSS/Atom)                  |
| `source_url`       | string   | Original site URL the user added (optional)    |
| `topic`            | string   | Caller-supplied, e.g. `"fcc"`, `"data-privacy"`|
| `discovery_method` | string   | `user` \| `autodiscover` \| `feedly` \| `rss_app` \| `scrapegraph` |
| `etag`             | string?  | Last seen `ETag` response header               |
| `modified`         | string?  | Last seen `Last-Modified` response header      |
| `status`           | enum     | `active` \| `paused` \| `error`                |
| `consecutive_errors` | int    | For exponential backoff / auto-pause           |
| `last_polled_at`   | timestamp| UTC                                            |
| `last_success_at`  | timestamp?| UTC                                           |
| `created_at`       | timestamp| UTC                                            |

**Unique index**: `feed_url` (case-insensitive, trailing-slash normalized).

### 3.2 `entries` collection

| Field          | Type     | Notes                                              |
|----------------|----------|----------------------------------------------------|
| `id`           | string   | ULID, primary key                                  |
| `feed_id`      | string   | FK → `feeds.id`                                    |
| `topic`        | string   | Denormalized from feed at ingest (fast filter)     |
| `guid`         | string   | `entry.id` or hash of `(link, title, published)`   |
| `title`        | string   |                                                    |
| `text`         | string   | `entry.content[0].value` else `entry.summary`, HTML-stripped |
| `link`         | string   | Canonical link to the article                      |
| `published_at` | timestamp| UTC, parsed from `published_parsed` / `updated_parsed` |
| `feed_url`     | string   | Denormalized for convenience                       |
| `ingested_at`  | timestamp| UTC, server wall-clock                             |

**Unique index**: `(feed_id, guid)` — dedupe key.
**Query index**: `(topic, published_at DESC)` — primary read pattern.
**Query index**: `(feed_id, published_at DESC)` — per-feed debugging.

### 3.3 Storage choice

**Firestore (Native mode)** in `us-central1`.

Rationale:
- Zero ops; scales to zero; Cloud Run native integration.
- Composite indexes cover our two query patterns.
- Pay-per-read fits the expected volume (~100 feeds × ~10 entries/day = ~1k writes/day; reads driven by upstream agent polls).

Fallback option if Firestore quotas become painful: Cloud SQL Postgres
(small `db-f1-micro`) with the same schema expressed as two tables. The
application code should abstract storage behind a `Repository` interface
so this swap is a contained change.

---

## 4. REST API

Base URL: `https://feed-service-<hash>-uc.a.run.app`
Auth: `Authorization: Bearer <API_KEY>` on every request.
Content type: `application/json` on all requests/responses.
Errors: `{ "error": "<code>", "message": "<human>" }` with appropriate 4xx/5xx.

### 4.1 `POST /feeds` — register a feed

```json
// request
{
  "feed_url":    "https://www.fcc.gov/news-events/headlines.xml",
  "source_url":  "https://www.fcc.gov",           // optional
  "topic":       "telecom",                        // required
  "discovery_method": "user"                       // optional, default "user"
}
```

```json
// 201 Created
{
  "id":           "01HWF3...",
  "feed_url":     "https://www.fcc.gov/news-events/headlines.xml",
  "topic":        "telecom",
  "status":       "active",
  "created_at":   "2026-04-22T18:00:00Z"
}
```

Side-effect: the service fetches the feed once synchronously (up to 10 s
timeout) to validate it. On failure returns `422` with the parsing
error and does **not** persist.

### 4.2 `GET /feeds` — list registered feeds

Optional query params: `topic`, `status`, `limit` (default 100, max 500),
`cursor` (opaque).

```json
// 200 OK
{
  "feeds": [ { ...feed fields... }, ... ],
  "next_cursor": "eyJ..."
}
```

### 4.3 `DELETE /feeds/{id}` — unregister

Soft-deletes: sets `status = "paused"`, keeps entries. `?hard=true` also
removes entries. Returns `204`.

### 4.4 `GET /entries` — query entries (the primary read endpoint)

Query params:

| Param       | Type     | Required | Default | Notes                                       |
|-------------|----------|----------|---------|---------------------------------------------|
| `topic`     | string   | no       | —       | Exact match. Repeatable for OR: `?topic=a&topic=b` |
| `since`     | ISO 8601 | no       | —       | `published_at >= since`                     |
| `until`     | ISO 8601 | no       | `now`   | `published_at < until`                      |
| `feed_id`   | string   | no       | —       | Restrict to one feed                        |
| `limit`     | int      | no       | 50      | Max 500                                     |
| `cursor`    | string   | no       | —       | Opaque pagination cursor                    |
| `order`     | enum     | no       | `desc`  | `desc` \| `asc` on `published_at`           |

```json
// 200 OK
{
  "entries": [
    {
      "id":           "01HWF3...",
      "feed_id":      "01HWE9...",
      "topic":        "telecom",
      "title":        "FCC opens proceeding on ...",
      "text":         "The Commission today...",
      "link":         "https://www.fcc.gov/document/...",
      "published_at": "2026-04-22T14:30:00Z",
      "feed_url":     "https://www.fcc.gov/news-events/headlines.xml"
    },
    ...
  ],
  "next_cursor": "eyJ..."
}
```

### 4.5 `GET /healthz` and `GET /readyz`

Liveness and readiness probes. No auth. Readiness checks Firestore
connectivity.

---

## 5. Polling subsystem

### 5.1 Scheduler

**Cloud Scheduler → Cloud Run** (HTTP push) every **15 minutes**:

```
cron:   */15 * * * *
target: POST https://feed-service/internal/poll-tick
auth:   OIDC token, audience = service URL
```

`/internal/poll-tick` is an internal endpoint (rejects requests without
valid OIDC from the scheduler's service account).

### 5.2 Tick handler

```
1. Read all feeds where status = "active".
2. Shard by hash(feed_id) % N to stay within Cloud Run request timeout.
3. For each feed, enqueue a Cloud Tasks job:
     POST /internal/poll-feed  { feed_id }
```

Using **Cloud Tasks** (not inline goroutines) gives us:
- Automatic retries with backoff.
- Per-feed timeouts without blocking other feeds.
- Natural rate-limit dispersion (the scheduler kicks off 100 tasks; Cloud
  Tasks drips them at a configurable rate).

### 5.3 Per-feed worker

`POST /internal/poll-feed { feed_id }`:

```
1. Load feed. Skip if status != "active".
2. feedparser.parse(url, etag=..., modified=...,
                    agent="RegulatoryIntel/1.0 (+contact@example.com)")
3. If response.status == 304: bump last_polled_at, return.
4. If response.bozo and no entries: increment consecutive_errors;
   if >= 5, set status = "error"; return.
5. For each entry:
     guid = entry.id or sha256(link + title + published)
     if not exists (feed_id, guid):
         insert entries row
6. Update feeds.etag, feeds.modified, last_polled_at, last_success_at.
   Reset consecutive_errors.
```

### 5.4 Etiquette

- Always send `If-None-Match` and `If-Modified-Since` when we have them.
- Honest `User-Agent` with contact URL.
- Minimum 15-minute poll interval per feed in v1 (override per-feed
  later if needed).
- Respect HTTP `429` / `Retry-After`: park the feed until that time.

---

## 6. Infrastructure (Cloud Run)

### 6.1 Services

| Service                | Purpose                     | Min instances | Max instances | Concurrency | Memory | CPU |
|------------------------|-----------------------------|---------------|---------------|-------------|--------|-----|
| `feed-service-api`     | Public REST API             | 0             | 10            | 80          | 512 Mi | 1   |
| `feed-service-worker`  | `/internal/poll-*` only     | 0             | 20            | 10          | 512 Mi | 1   |

Two separate services so a burst of polling can't starve read traffic,
and so the API can scale to zero cheaply at night.

### 6.2 Networking

- **Ingress** = `internal-and-cloud-load-balancing` for the worker
  service (only Cloud Scheduler and Cloud Tasks can reach it).
- **Ingress** = `all` for the API service, with the API-key check as the
  security boundary.
- **Egress** = **VPC connector → Cloud NAT with reserved static IP**.
  This gives the polling traffic a stable source IP so WAF reputation
  accrues over time — critical for Akamai-protected regulator sites.

### 6.3 IAM

- `feed-service-runtime@...iam.gserviceaccount.com` — single SA for both
  services.
  - Role: `roles/datastore.user` (Firestore RW).
  - Role: `roles/cloudtasks.enqueuer` (API → worker).
  - Role: `roles/secretmanager.secretAccessor`.
- Cloud Scheduler SA → `roles/run.invoker` on the worker service.
- Cloud Tasks SA → `roles/run.invoker` on the worker service.

### 6.4 Secrets

Stored in Secret Manager, mounted as env vars:

- `FEED_SERVICE_API_KEY` — bearer token for the public API.
- `FEEDLY_API_TOKEN` — (only if Feedly discovery is later added upstream;
  not needed here since discovery is out of scope).

### 6.5 Deployment

- **Image**: `gcr.io/<project>/feed-service:<git_sha>`.
- **Build**: Cloud Build triggered from `main` branch.
- **Rollout**: `gcloud run deploy` with `--tag=canary --no-traffic`,
  manual `--to-revisions=<rev>=100` after smoke test.
- **IaC**: Terraform module in `infra/feed_service/` — Cloud Run
  services, Scheduler job, Tasks queue, Firestore indexes, NAT, SA
  bindings, Secret Manager entries.

### 6.6 Observability

- **Structured logs** (JSON) with `feed_id`, `request_id`, `topic`,
  `http_status` on every polling event.
- **Cloud Monitoring dashboards**:
  - p50/p95 poll duration
  - Feeds in `error` status (alert if > 5 % of total)
  - Entries/hour ingest rate (alert on 2 h of zero)
  - API p95 latency, 5xx rate
- **Alerts** via Cloud Monitoring → PagerDuty or email.

---

## 7. Costs (rough estimate, 100 feeds)

| Component          | Monthly cost          |
|--------------------|-----------------------|
| Cloud Run (both)   | $5 – $15              |
| Firestore          | $1 – $5               |
| Cloud Scheduler    | free tier             |
| Cloud Tasks        | free tier             |
| Cloud NAT + static IP | ~$5                |
| **Total**          | **~$15–25/month**     |

---

## 8. Security

- All write endpoints require the API key.
- Read endpoints also require the API key (simpler than splitting; no PII).
- TLS terminated by Cloud Run (Google-managed cert).
- No persistence of API keys in logs — redaction middleware.
- Firestore rules prohibit direct client access (service-to-service only).

---

## 9. Implementation checklist

- [ ] Repo layout: `feed_service/{api,worker,shared}/`, `tests/`, `infra/`.
- [ ] `shared/models.py` — Pydantic models matching §3.
- [ ] `shared/repo.py` — `FeedRepository`, `EntryRepository` interfaces.
- [ ] `shared/repo_firestore.py` — implementation.
- [ ] `api/main.py` — FastAPI app, endpoints in §4.
- [ ] `worker/main.py` — `/internal/poll-tick`, `/internal/poll-feed`.
- [ ] `worker/poller.py` — `feedparser` polling logic (§5.3).
- [ ] `Dockerfile` — slim Python 3.11, uvicorn, gunicorn workers.
- [ ] `infra/feed_service/*.tf` — Terraform.
- [ ] `.github/workflows/deploy.yml` or Cloud Build YAML.
- [ ] Integration test: register a feed, force a poll, assert entries appear.
- [ ] Load test: 1k feeds, simulate one poll cycle, assert p95 < 10 min.

---

## 10. Open questions

1. **Topic taxonomy**: should `topic` be a free-form string or constrained
   to an enum maintained upstream? v1 says free-form; revisit if topic
   drift becomes painful.
2. **Full-text search**: not in scope, but an eventual need. Firestore
   doesn't do FTS natively. Options: Meilisearch on Cloud Run, or
   BigQuery export for ad-hoc SQL queries.
3. **Historical backfill**: when a feed is first registered, do we walk
   its archive if available? v1 says no (we store only what appears in
   the feed at poll time). Revisit if users ask.
4. **Multi-region**: v1 is `us-central1` only. Firestore Native is
   multi-region by default; services can be cloned to `eu-west1` later
   if needed for EU regulators.
