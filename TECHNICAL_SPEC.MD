# TECHNICAL_SPEC.md — Rostral Technical Specification

## 1. 🎯 Project Goal

Develop an open-source platform for semantic monitoring of online changes with AI-powered analysis:
- Track websites, RSS feeds, APIs, and PDFs  
- Flexible YAML-based configuration  
- Deep AI summaries (OpenAI, GPT4All, Hugging Face)  
- Self-hosted and SaaS deployment modes  

## 2. 🧱 Architecture

- Configs: `monitors/*.yaml`  
- Core: Python, ThreadPoolExecutor / Celery, Redis, SQLAlchemy  
- Database: SQLite (MVP), PostgreSQL (production)  
- Web UI: Flask/FastAPI + Jinja/HTMX  
- Pipeline: `fetch → extract → normalize → alert → gpt → store`  
- Alerts: Apprise (Telegram, Email, Discord, Webhook, ntfy)  
- Search: SQLite FTS5 → Elasticsearch  
- Deployment: Docker Compose, Railway, Render, Fly.io, VPS + supervisord  

## 3. 📄 YAML Monitoring Config

```yaml
name: "Monitor Name"
type: rss|html|api|pdf
url: "https://example.com/feed"
fetch:
  cache: true
  ttl: 900
  proxy_group: default
  rate_limit: "1req/30s"
  retry_policy:
    max_retries: 3
    backoff_factor: 2
extract:
  css: "#content"
normalize:
  trim: true
gpt:
  prompt: "Summarize key changes..."
```

## 4. 🗂️ Event Storage

The system stores detected changes and AI-processed results in a structured event table. It supports both SQLite and PostgreSQL backends.

| Field         | Type        | Description                          |
|---------------|-------------|--------------------------------------|
| `id`          | UUID / PK   | Unique event identifier              |
| `monitor_id`  | UUID / FK   | Associated monitor reference         |
| `url`         | TEXT        | Source URL of the event              |
| `title`       | TEXT        | Event title or content heading       |
| `published_at`| TIMESTAMP   | Publication or detection timestamp   |
| `summary_quick` | TEXT     | Fast extracted summary               |
| `gpt_summary` | TEXT        | AI-generated interpretation          |
| `tags`        | TEXT[]      | Optional tags assigned               |
| `score`       | INTEGER     | Assigned importance or priority      |
| `geo`         | JSONB       | Optional geolocation metadata        |
| `status`      | TEXT        | Event processing state (`new`, `done`, etc.) |
| `alert`       | BOOLEAN     | Whether notification is needed       |
| `flags`       | TEXT[]      | Error or processing flags            |
| `screenshot`  | TEXT        | Path or URL to stored snapshot       |

- DB backend can be switched via `DB_ENGINE` environment variable  
- Alembic migration scripts support PostgreSQL schema evolution

## 5. 🧠 AI Summarization

Rostral supports multi-model AI summarization for interpreting content changes and generating human-readable reports.

### Supported Models

- **OpenAI GPT-4** (via API)
- **GPT-3.5-turbo**
- **Local LLMs** (e.g. GPT4All, GGUF via llama.cpp or Ollama)

### Features

- Customizable prompts per monitor  
- Support for few-shot prompting and template variables  
- Fallback mechanism: if AI fails or times out, use `summary_quick`  
- Prompt reuse across templates via community catalog

### Testing & Reliability

- **Unit tests** for summarization field structure and content validity  
- **Integration tests** on real-world HTML, RSS and PDF examples  
- Configurable **retry and timeout** behavior per monitor  
- Planned support for async summarization queue with Celery

### Extensibility

- Shared prompt registry: `prompts/*.txt`  
- Configurable in YAML per monitor  
- Accepts PRs with new prompt types and model backends

## 6. 🔔 Alerts and Prioritization

Rostral allows defining rule-based alerts directly within each YAML monitor configuration. These alerts help prioritize important changes and notify users when specific patterns are detected.

### YAML Example

```yaml
alerts:
  - match: ["keyword1", "urgent topic"]
    score: 7
    alert: true
    notify: 
      - telegram://your-bot-token@your-channel
      - email://you@example.com
```

### Fields

- match: list of strings to match against extracted content (title, summary, etc.)
- score: integer from 1–10 indicating the event’s priority level
- alert: if true, the event will be marked for notification
- notify: list of Apprise-compatible endpoints for alert delivery

### Behavior

- Events with alert: true are eligible for notification routing  
- The score field influences sorting, filtering, and visual weight in the dashboard  
- Alert matching is case-insensitive and keyword-based (no regex in MVP)

### Notification System

Rostral integrates with the Apprise notification framework, supporting:

- Telegram  
- Email (SMTP)  
- Discord  
- Webhooks  
- ntfy, Gotify, Pushover, and others

Notifications use Jinja2 templates, allowing monitor-specific or global message layouts.

### Future Enhancements

- Adaptive alert scoring (AI-based prioritization)  
- Alert deduplication and grouping  
- Interactive rule testing via UI or CLI  
- Rule sets defined centrally and reusable across monitors

## 7. 📁 Full-Text Document Storage

Some monitors—particularly for legal filings, public tenders, and government bulletins—fetch long-form documents. Rostral supports the storage and retrieval of full-text content for deep inspection and future semantic use.

### Storage Strategy

- **Raw text is extracted** during normalization and stored in compressed format
- Supports:
  - **BLOB storage** in the database (e.g. for SQLite use cases)
  - **File-based storage** with hashed paths or monitor-scoped directories
- Compression via **gzip** to optimize disk space and transmission

### Document Metadata

- Linked to events via `event_id`
- File structure includes:
  - `.txt.gz` or `.json.gz` source files  
  - Optional raw HTML archive (`.html`)  
  - `document_id`, `created_at`, `source_type`

### Web UI Support

- Document preview in UI:
  - “Show full text” collapsible section
  - Pagination or expandable field
  - Optional keyword-highlighting

### Future Extensions

- **RAG (Retrieval-Augmented Generation)** features, e.g. answer questions from past documents  
- **Semantic vector search** over full-text corpora  
- **Document deduplication** and clustering

  ## 8. 🌐 Web Interface (Dashboard)

The Rostral web interface provides a lightweight and accessible control panel for managing monitors, reviewing detected events, and interacting with templates and alerts.

### Features

- **Event Feed**
  - Tabular or card view of recent events
  - Sort and filter by date, score, tag, monitor
  - Visual indicators for `alert`, `error`, or `new`
  - Click-through to full summary and raw document

- **Monitor Management**
  - List of active and paused monitors
  - Actions: view logs, edit YAML, run now, pause/resume
  - Integrated YAML editor with real-time validation
  - Cron scheduling support (manual + cron format)

- **Template Catalog**
  - Browse featured universal and deep-dive templates
  - One-click “Use this” to clone into a personal monitor
  - Template descriptions and filtering by category

- **Inline Assistance**
  - Context-sensitive tooltips and examples
  - Quickstart walkthrough for new users
  - Embedded links to documentation

### UI Stack

- **Frontend**: Jinja2 templates + HTMX/Alpine.js for dynamic interactivity  
- **Backend**: Flask (MVP) or FastAPI (SaaS-ready)  
- **Theme**: Custom Bootstrap / Tailwind hybrid  
- **Assets**: Rendered from `static/`, config-driven branding

### Roadmap

- Saved views and smart filters  
- Public/embedded monitors with shareable links  
- Keyboard navigation and command palette  
- Drag-and-drop YAML builder (experimental)

  ## 9. 🔐 Authorization and Access Control

Rostral supports flexible authentication and access control, suitable for both self-hosted instances and multi-tenant SaaS deployments.

### Modes

- **Self-Hosted Mode**
  - Lightweight auth via Basic Auth or JWT tokens
  - Configurable admin credentials via `.env`
  - No external identity provider required

- **SaaS Mode**
  - Full user model with email/password login
  - User roles: `admin`, `editor`, `viewer`
  - Multi-tenant architecture (organization-based scoping)

### User Model

```sql
users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT CHECK(role IN ('admin', 'editor', 'viewer')),
  created_at TIMESTAMP DEFAULT now()
)

- Passwords hashed using bcrypt or argon2  
- Optional fields: lastlogin, disabled, orgid

### Monitor Visibility

- Each monitor includes:
  - owner_id (references users.id)  
  - visibility: private or public  
  - Access-controlled via role and tenant scope  

### Bootstrap and Seeding

- On first launch:
  - Auto-create admin account (email/password via .env)
  - Optionally create a demo user and sample monitors
- Support for seeding via seed_users.py or SQL migrations

### Roadmap

- OAuth 2.0 and OpenID Connect (GitHub, Google)  
- Team-based access via workspace invitation  
- Per-monitor access policies and audit logs

## 10. 📦 Template Catalog

Rostral provides a growing library of ready-made YAML templates that cover both generic monitoring cases and deep-dive domain-specific use cases.

### 10.1 Universal Templates

Stored under: `templates/universal/`

These templates are designed for broad, everyday monitoring scenarios and easy onboarding.

Examples:

- `github_releases.yaml` — Track new releases from GitHub repositories
- `amazon_price.yaml` — Monitor product price changes on Amazon
- `wiki_changes.yaml` — Follow live edits to specific Wikipedia pages
- `job_postings.yaml` — Track new jobs from public job boards (e.g. Indeed, HH.ru)

**Features**:
- Minimal configuration required  
- Straightforward `url` + `css` + optional `alerts`  
- Great for tutorials and quick-start workflows

---

### 10.2 Deep-Dive Templates

Stored under: `templates/deep-dive/`

These templates are designed for complex or high-value domains that require precise configuration or AI-driven post-processing.

Examples:

- `44fz_tenders.yaml` — Monitor Russian public procurement tenders (zakupki.gov.ru)
- `court_decisions.yaml` — Watch for new judicial rulings from online registries
- `complexpdfreports.yaml` — Track lengthy PDF bulletins with nested table parsing

**Features**:
- Use multiple pipeline stages: `extract`, `normalize`, `gpt`, `alert`
- Include prompt customization and multi-field filtering  
- Can be integrated into SaaS workflows with enhanced capabilities

---

### Template Structure

Each template includes:

- A standalone YAML config (`*.yaml`)  
- Inline comments and prompt examples  
- Metadata (title, description, tags)  
- README stub (`README.md`) inside each folder (optional)

---

### Roadmap

- Indexed template browser in UI (filter by source type, tags, language)  
- Community-driven template submission (PR-based)  
- Template testing runner: `rostral test --template path/to/*.yaml`  
- Documentation site with rendered preview and examples

  ## 11. 🔍 Search and Filtering

Rostral provides full-text and structured search capabilities to help users locate relevant events quickly and efficiently.

### Text Search (FTS)

- Uses **SQLite FTS5** for local or lightweight deployments  
- Searchable fields:
  - `title`
  - `summary_quick`
  - `gpt_summary`
  - `tags`
- Supports:
  - Phrase and token search (e.g. `"court ruling"` or `tender`)  
  - Partial match and prefix search (`procure*` → `procurement`)  
  - Case-insensitive lookups

### Structured Filtering

Available via CLI and Web UI:
- `monitor_id`
- `score` (e.g. score ≥ 5)
- `alert = true`
- `status = error | done`
- `tags` includes value
- Date range (`published_at` between X and Y)

### Saved Views and Presets

- UI allows saving filter combinations (e.g. “Legal Alerts Last 7 Days”)
- Presets stored per user or workspace
- Available as buttons, dropdowns, or URLs with query params

### Search Performance

- For production-scale deployments, supports migrating to:
  - **PostgreSQL + pg_trgm**
  - **Elasticsearch or OpenSearch** index backend

### Roadmap

- Semantic vector search via embeddings (`RAG-ready`)  
- Cross-template queries and dashboard-wide filters  
- Query builder with visual DSL (e.g. `score > 5 AND tag:ai`)

## 12. 🧑‍🤝‍🧑 Collaboration

Rostral is designed to support team-based workflows and multi-user access, enabling collaborative monitoring at scale.

### Workspaces and Projects

- Users belong to one or more **workspaces** (e.g. organizations or departments)
- Each workspace contains:
  - Monitors
  - Event feeds
  - Saved templates
  - Users and access controls

- Optionally support:
  - **Project-level scoping** inside a workspace (e.g. “Legal Watch”, “Market Feeds”)

### Roles and Permissions

- **Owner**: Full access; can manage users and billing  
- **Editor**: Can create/edit monitors, templates, and alerts  
- **Viewer**: Read-only access to events and templates

Future support for:
- Fine-grained access control per monitor  
- Role-based access to specific alert channels or templates

### Comments and Annotations

- Users can comment on specific events in the feed  
- Comments include:
  - `author`, `timestamp`, `event_id`, `body`, `tags[]`
- Notifications on mentions or threads
- Support for markdown formatting and @mentions

### Activity Feed and Audit Logs

- Per-workspace feed of:
  - Monitor edits
  - User logins
  - Comments, alerts triggered
- Viewable in UI and exportable (JSON, CSV)

### Roadmap

- Real-time collaboration (edit locks, live presence)  
- Comment reactions and resolution flow  
- Shared saved filters and dashboards  
- Monitor handoff & delegation workflows

## 13. 💬 Notifications and Integrations

Rostral supports flexible, pluggable notification delivery using the [Apprise](https://github.com/caronc/apprise) library, along with template-based message formatting and extension points for deeper system integration.

### Notification System

- Each monitor defines its own `notify:` targets in YAML  
- Supports sending alerts to multiple channels simultaneously  
- Alert content is rendered via **Jinja2 templates**

### Supported Channels via Apprise

- Telegram  
- Email (SMTP, Gmail)  
- Discord  
- Slack (via webhook)  
- ntfy  
- Pushover  
- Webhook (custom HTTP POST)
- Matrix  
- Gotify  
- XMPP and more

### Template Customization

- Global and per-monitor notification templates
- Written in Jinja2 with access to:
  - `event` metadata (title, score, URL, timestamp)  
  - `summary_quick`, `gpt_summary`, `monitor.name`  
  - `document_link` if applicable

Example:

```jinja2
🔥 [{{ monitor.name }}] {{ event.title }}

{{ summary_quick }}

🔗 {{ event.url }}
📎 Tags: {{ tags | join(', ') }}
```

### Extensibility via Plugin API

- Rostral exposes a Python-based plugin interface:
  - oneventcreated(event)  
  - onalerttriggered(event, channel)  
  - custom_notifier(event, template, config)
- Allows:
  - Logging alerts to external systems  
  - Creating custom transports (e.g. SMS, mobile push)
  - Integrating with incident management platforms (e.g. PagerDuty, OpsGenie)

### Roadmap

- Rate limiting and retry for noisy monitors  
- Notification dashboards and delivery history  
- Slack-block formatting and Markdown rendering  
- Alert acknowledgment via webhook reply or UI button

## 14. 💰 Licensing and Commercial Tiers

Rostral is released as an open-core project under a permissive open-source license, with optional commercial tiers designed to support sustainable development and advanced use cases.

### Open Source Edition

- **License**: Apache License 2.0  
- **Includes**:
  - Core pipeline: fetch → extract → normalize → store  
  - YAML config engine and CLI runner  
  - Basic Web UI with monitor management and feed viewer  
  - SQLite support  
  - Default alerting with Apprise  
  - Community templates (universal and deep-dive)

Intended for:
- Personal use, self-hosted deployments  
- Civic tech, nonprofits, research, and experimentation  
- Developer customization and contributions

---

### Pro (SaaS) Tier *(Planned)*

- Hosted Rostral instance with:
  - GPT-4 access (via API key or pre-billed credits)  
  - Long-term event storage and full history  
  - Webhooks, ntfy, email digest alerts  
  - User onboarding, password reset, and workspace sharing  
  - Usage-based pricing (monitors, API calls, GPT tokens)

Ideal for:
- Journalists, data analysts, and small teams  
- Organizations needing no-dev setup  
- Custom use-case templating with UI-first editing

---

### Enterprise Tier *(Planned)*

- White-labeled SaaS or on-premises  
- Features:
  - Multi-tenant isolation  
  - Single Sign-On (SSO) integration  
  - SLA-backed support and roadmap influence  
  - Dedicated onboarding and consulting  
  - Secure document handling and encryption policies

Targeted at:
- Governmental or corporate clients  
- NGOs with sensitive data compliance  
- SaaS integrators embedding Rostral logic

---

### Marketplace Ecosystem *(Optional Roadmap)*

- **Template marketplace** for paid YAML scenarios and integrations  
- **Consulting services** around custom pipelines and prompt engineering  
- Revenue-sharing model for contributors

---

### Compliance

- GDPR-ready data separation (by workspace/user)  
- No user activity is shared outside the platform without consent  
- Token limits and rate throttling for GPT/API usage

## 15. 🧾 Configuration Validation and Schema Support

Rostral ensures the correctness, stability, and safety of all monitor configurations through formal validation tools and schema definitions.

### Configuration Schema

- Located at: `docs/SCHEMA.md`
- Defines a JSON Schema covering all supported fields and structures of `monitor.yaml`
- Includes:
  - Required and optional fields  
  - Allowed types and enums  
  - Default values and fallback behavior  
  - Version compatibility notes

Usage:

```bash
rostral validate monitor.yaml
`
---

### Default Configuration

- File: defaults.yaml
- Contains global default values for common fields:
  - ttl
  - retry_policy
  - proxy_group
  - normalize.trim
  - alert.defaults
- Loaded at runtime and merged unless overridden per-monitor

---

### Validation Tools

- Script: validate_yaml.py
- Performs:
  - JSON Schema compliance check  
  - Reserved field protection  
  - Duplicate key detection  
  - Optional semantic linting (e.g. bad prompt templates)

---

### Versioning

- Every config MUST declare a version: field
  - Example: version: 1.0
- Helps prevent runtime breakage from incompatible changes
- Schema evolution tracked in GitHub

---

### Testing

- All templates in templates/ and examples/ are tested against schema  
- CI (GitHub Actions) runs validate_yaml.py on:
  - Pull Requests  
  - Commits to main and release branches  
- Fail-fast policy on invalid YAML

---

### Roadmap

- VS Code extension for YAML autocompletion  
- Inline schema-driven tooltips in the web editor  
- Machine-readable changelogs for schema diffs         

 ## 16. 🚀 Deployment

Rostral is designed for fast local setup with Docker, as well as scalable cloud deployments using modern PaaS infrastructure.

### Local Development (Docker)

```bash
git clone https://github.com/your-org/rostral.git
cd rostral
cp .env.example .env
docker-compose up --build

`

- Local SQLite database by default  
- Admin and demo users seeded automatically  
- All services (API, web, workers) run in isolated containers

### Configuration

- Environment configuration via .env  
- Secrets (API keys, DB credentials) injected using Docker secrets or mounted volumes  
- Configurable flags:
  - DB_ENGINE = sqlite | postgres
  - DEBUG = true | false
  - ENABLE_WORKER = true | false

### Cloud & PaaS Options

Supported or planned:

Provider  Notes
Railway  1-click deploy + PostgreSQL integration
Render  Background workers + custom domains
Fly.io  Deploy to edge locations, lightweight Redis
VPS  Manual deploy via Docker, supervisord/nginx

CI/CD Pipeline

- GitHub Actions included by default:
  - Lint, test, validate YAMLs  
  - Build and push Docker images  
  - Trigger one-click deploy hooks
- ci/ directory contains reusable workflow templates

One-Click Deployment (Planned)

- Auto-provisioning script for:
  - Admin credentials setup  
  - Default monitor templates  
  - Config validator  
  - UI + API ready-to-use on subdomain

---

### Roadmap

- Helm charts for Kubernetes  
- Prebuilt DockerHub images  
- CLI deploy command (rostral deploy --env prod)  
- Support for autoscaling Celery workers

## 17. 📌 Identity and Branding

### Project Name

**Rostral**

- Inspired by the Latin word *rostrum*, meaning "a platform for public speech" — symbolizing structured communication and clarity.
- Metaphorically represents extracting meaningful information from a stream of raw input.

### Domain and Repository

- Primary domain: **rostral.io**
- GitHub repository (tentative): `github.com/rostralhq/rostral`

### Slogan

> **All you need in one feed** — AI-powered monitoring for anything

Multilingual variants:

- 🇷🇺 Russian: Всё что нужно в одной ленте  
- 🇪🇸 Spanish: Todo lo que necesitas en un solo feed

### Branding Assets (Planned)

- SVG logo and wordmark in light/dark variants  
- Social preview image (`social.png`)  
- Favicon and app icon pack (`favicon.ico`, `apple-touch-icon.png`)  
- Color palette and typography spec (`branding.md`)  

### Roadmap

- Branding kit download for contributors and forked projects  
- README header redesign with CTA buttons  
- Open Graph preview for Docs and SaaS subdomains

18. 🧭 Positioning and Use Case Scenarios

Rostral is designed to serve both general-purpose monitoring and specialized intelligence gathering across sectors. Its branding and template structure reflect this dual-layered communication model.

18.1 Two-Tier Messaging Strategy

1. Universal Monitoring Layer
For casual and practical everyday users.

Slogan:  
> All you need in one feed

Example Use Cases:
- Track product prices from e-commerce sites  
- Get notified about new job listings or freelance gigs  
- Monitor changelogs or releases from GitHub  
- Follow regional news or classifieds from a favorite site  

Positioning Keywords:  
lightweight · YAML-first · no-code · browser-friendly

---

2. Deep-Analysis Layer
For researchers, journalists, policy analysts, and teams needing semantic depth.

Sub-slogan:  
> From simple price changes to deep analysis of legal documents

Use Cases:
- Detect and summarize new tenders in procurement registries  
- Monitor PDF bulletins from government agencies  
- Capture changes in legislative or regulatory announcements  
- Scrape and normalize structured data from court or budget APIs

Positioning Keywords:  
AI summaries · PDF parsing · clustering · multilingual · compliance

---

18.2 Template Directory Structure

Rostral groups its templates according to complexity and domain scope:


templates/
  ├── universal/        # Easy onboarding, plug-and-play scenarios
  │     ├── github_releases.yaml
  │     ├── amazon_price.yaml
  │     └── job_postings.yaml
  └── deep-dive/        # Complex sources with AI/post-processing
        ├── 44fz_tenders.yaml
        ├── court_decisions.yaml
        └── complexpdfreports.yaml


Roadmap for Positioning

- Landing page variations by user segment: developers, analysts, NGOs  
- Case studies: how specific YAMLs led to real-world insights  
- SEO keywords: “semantic monitoring”, “GPT-driven alerts”, “monitor PDFs with AI”  
- Partner ecosystem: civic tech orgs, data journalists, research collectives


## 19. 🛠 Next Steps and Implementation Plan

This section outlines the high-priority development actions for finalizing the Rostral MVP and preparing for open-source and SaaS readiness.

### 🔹 Configuration and Schema

- Finalize and freeze `TECHNICAL_SPEC.md` as version `v1.0`  
- Write `SCHEMA.md` covering all YAML field types and rules  
- Validate `defaults.yaml` and `validate_yaml.py` against example templates  
- Add automated schema tests in CI  

---

### 🔹 Template Catalog

- Prepare `templates/universal/` and `templates/deep-dive/` directories  
- Write README stubs and field-level inline comments per template  
- Add metadata field block (e.g. `version`, `tags`, `category`)  
- Test all initial templates using `rostral validate` and sample runs  

---

### 🔹 CLI and Core Runner

- Implement `cli.py` entrypoint: `rostral monitor path/to/*.yaml`  
- Support for:
  - Dry-run vs continuous mode  
  - `--log-level`, `--once`, `--cron`, `--profile` flags  
- Debug view: show pipeline stages and summaries as plaintext  
- Unit tests for fetch, normalize, and gpt stages  

---

### 🔹 Self-Hosted Deployment

- Create `docker-compose.yml` for SQLite + Redis + app  
- Prepare `.env.example` and `.env.template`  
- Seed:
  - One admin user  
  - One demo user  
  - 2-3 universal sample monitors  
- Test deploy on Render or Railway  

---

### 🔹 Web UI and SaaS Alpha

- Build Flask-based web dashboard MVP  
- Pages:
  - Login, Feed, Monitors, Templates, Settings  
- Integrate validation and inline YAML editor  
- Add alert notification rendering and event detail view  
- Prepare SaaS boilerplate:
  - Multi-user DB schema  
  - Signup / reset password / roles

---

### 🔹 CI and GitHub Readiness

- Add GitHub Actions for:
  - Lint + test  
  - YAML validation  
  - Docker build  
- Write `CONTRIBUTING.md` and issue templates  
- Create `docs/` folder with index and markdown navigation  

---

### 🔹 Branding and Preview

- Add `README.md`, `branding.md`, and SVG logo  
- Create Open Graph preview (`social.png`)  
- Configure GitHub Pages or Netlify preview  
- Buy domain `rostral.io` or configure DNS  

---

### 🗓 Suggested Timeline

| Week | Milestone                                           |
|------|-----------------------------------------------------|
| 1    | Spec freeze, YAML schema, initial CLI runner        |
| 2    | Docker setup, validator, example templates tested   |
| 3    | Web UI MVP, account system, alert rendering         |
| 4    | SaaS alpha with multi-user demo + basic billing UX  |
