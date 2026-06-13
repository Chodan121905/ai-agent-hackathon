# 🛡️ Scam Guardian — Build Plan (Backend-first, Telegram, multi-phase LangGraph agent)

> This is the **authoritative technical plan**. [README.md](README.md) is the product/market pitch and stays as-is.
> Where the README says **WhatsApp**, we build on **Telegram** instead (rationale in §1). The business model, market,
> and demo narrative in the README are channel-agnostic and still hold.

**Scope of this phase:** build the **backend only**, but design every contract so a **web app (React/TS)** and a
**Flutter (Dart) mobile app** can be added later with zero backend rework. The scam-detection "brain" is a
**multi-phase agent built on LangChain + LangGraph**.

---

## Table of contents
1. [What changed vs. the README](#1-what-changed-vs-the-readme)
2. [Architecture (updated)](#2-architecture-updated)
3. [Tech stack & why](#3-tech-stack--why)
4. [Repository layout (monorepo)](#4-repository-layout-monorepo)
5. [The multi-phase LangGraph agent](#5-the-multi-phase-langgraph-agent)
6. [The shared contract: Verdict schema](#6-the-shared-contract-verdict-schema)
7. [Sponsor integrations (verified, with fallbacks)](#7-sponsor-integrations-verified-with-fallbacks)
8. [Data model](#8-data-model)
9. [API surface](#9-api-surface)
10. [Telegram bot design](#10-telegram-bot-design)
11. [Web + Flutter readiness (OpenAPI codegen)](#11-web--flutter-readiness-openapi-codegen)
12. [Configuration & secrets (.env)](#12-configuration--secrets-env)
13. [Milestones / build order](#13-milestones--build-order)
14. [De-risking & key decisions](#14-de-risking--key-decisions)
15. [Local dev & run](#15-local-dev--run)
16. [Success criteria](#16-success-criteria)
17. [Open questions / assumptions](#17-open-questions--assumptions)

---

## 1. What changed vs. the README

| README says | This plan does | Why |
|---|---|---|
| WhatsApp via Twilio sandbox | **Telegram bot** | Free, no Twilio account/credits, instant `@BotFather` setup; native handling of **text / photo / voice / link**; a bot can **proactively message** a guardian (the family-alert loop) and **broadcast** "scam of the week" with no paid messaging tier. Webhook plugs straight into our FastAPI app. |
| "Kimi agent swarm (read + verify)" | **LangGraph state machine** with parallel `analyze ∥ verify` nodes | Gives us the swarm as an explicit, debuggable, resumable graph instead of ad-hoc calls. "Multi-phase using LangChain" = LangGraph (the LangChain ecosystem's agent engine). |
| One-day full-stack build | **Backend-first**, contract-driven | We ship the brain + API + bot now; web and Flutter consume the same OpenAPI contract later. |

**Telegram-specific constraint to design around (high-confidence):** a bot **cannot** message a user who has never
pressed `/start`. So the guardian must start the bot once; we capture their `chat_id` then. This drives the
**pairing-code onboarding** in §10.

---

## 2. Architecture (updated)

```
 Telegram (forwarded text / screenshot / voice note / link)
        │  webhook POST (HTTPS)
        ▼
 FastAPI  ── POST /telegram/webhook ──┐         (web + Flutter call the SAME core via POST /api/v1/check)
        │   ack fast, run agent in     │
        │   BackgroundTask             │
        ▼                              ▼
 ┌──────────────────── LangGraph multi-phase agent ────────────────────┐
 │  PHASE 1  intake/normalize   → detect modality + language hint       │
 │  PHASE 2  route (cond. edge) → fan-out by modality                   │
 │  PHASE 3  extract (parallel):                                        │
 │            • image  → SenseNova U1  (OCR/vision)   ⟂ Kimi-vision fallback
 │            • voice  → Whisper (primary) / VideoDB  → transcript      │
 │            • link   → Bright Data (WHOIS/SERP/brand) + Daytona (safe open)
 │            • text   → passthrough                                    │
 │  PHASE 4  analyze ∥ verify   (the "swarm")                           │
 │            • analyze → Kimi k2.6 tactic detection                    │
 │            • verify  → tools: link reputation, brand-domain match,   │
 │                        this-week scam cross-ref (ToolNode)           │
 │  PHASE 5  synthesize → strict Verdict JSON (with_structured_output)  │
 │            written in the user's language                            │
 │  PHASE 6  decide (cond. edge) → reply • log to DB • alert family     │
 └──────────────────────────────────────────────────────────────────────┘
        │                         │                          │
        ▼                         ▼                          ▼
 reply to the elder       persist report (DB)        if risk=high → bot.send_message(guardian)
        (all LLM calls routed via TokenRouter gateway; Kimi pinned as the brain)
        │
        └── aggregated reports feed → GET /api/v1/intelligence/trends  (B2B data product / dashboard)
```

---

## 3. Tech stack & why

| Layer | Choice | Notes (verified June 2026) |
|---|---|---|
| Language | **Python 3.12+** | LangGraph is Python-first; pairs cleanly with FastAPI. |
| Web framework | **FastAPI** + Uvicorn | Async, auto **OpenAPI 3.1** → the single shared contract for web + Flutter. |
| Schemas | **Pydantic v2** | Request/response + the `Verdict` contract. Required by current langchain-core. |
| Agent engine | **LangGraph 1.2.x** (`langgraph>=1.2,<2`) + `langchain>=1.3,<2` + `langchain-openai>=1.2,<2` | StateGraph, conditional edges, `Send` fan-out, `ToolNode`, `with_structured_output`. |
| LLM "brain" | **Kimi k2.6** (Moonshot), OpenAI-compatible | `base_url=https://api.moonshot.ai/v1`, model id `kimi-k2.6` (**dot, not dash**), 256K ctx, vision + `json_schema` output. |
| LLM gateway | **TokenRouter** (OpenAI-compatible) | `base_url=https://api.tokenrouter.io/v1`; route cheap triage `auto:cost`, pin Kimi for the verdict. Env-flippable. |
| Telegram | **python-telegram-bot v22** (`[job-queue]`) | Webhook under FastAPI lifespan; `JobQueue` for scam-of-week broadcast. |
| DB | **Supabase Postgres** via **SQLModel + SQLAlchemy 2.0 async + asyncpg** | Supabase MCP is already connected to this project. SQLite fallback for offline dev. |
| Migrations | **Alembic** | Run against the **direct** (5432) Supabase connection. |
| STT | **faster-whisper** (primary, multilingual) / **VideoDB** (sponsor path) | VideoDB lacks Malay & Tamil — see §14. |
| Screenshot OCR | **SenseNova U1** (sponsor) / **Kimi-vision** (fallback) | SenseNova also generates the scam-of-week card. |
| Link intel | **Bright Data** (Web Unlocker + SERP) + **Daytona** (sandbox) | Compose WHOIS-age + brand-lookalike + this-week cross-ref. |
| Slow work | **FastAPI BackgroundTasks** (hackathon) → **ARQ + Redis** (if retries needed) | Never run the agent inline in the Telegram webhook (retry storm). |
| Dev HTTPS | **cloudflared tunnel** | Free, unlimited; ngrok free tier now caps at 2h. |
| Deploy (demo) | local + cloudflared, or paid Render/Railway window | Render free tier cold-starts (~30–50s) — bad for a live webhook demo. |

---

## 4. Repository layout (monorepo)

```
ai-agent-hackathon/
├── README.md                 # product/market pitch (unchanged)
├── PLAN.md                   # this file
├── .gitignore                # Python + Flutter + web
├── backend/                  # ← all work this phase
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py           # FastAPI app, lifespan (PTB init + set_webhook), CORS
│   │   ├── core/
│   │   │   ├── config.py     # pydantic-settings BaseSettings
│   │   │   ├── db.py         # async engine + get_session()
│   │   │   └── logging.py
│   │   ├── models/           # SQLModel table=True ORM models
│   │   ├── schemas/          # Pydantic v2 request/response (incl. Verdict) = the CONTRACT
│   │   ├── api/
│   │   │   ├── deps.py       # auth + db-session dependencies
│   │   │   └── routers/
│   │   │       ├── check.py        # POST /api/v1/check  (core, reused by all clients)
│   │   │       ├── reports.py      # report history
│   │   │       ├── guardians.py    # pairing / family loop
│   │   │       ├── intelligence.py # dashboard data product
│   │   │       └── telegram.py     # POST /telegram/webhook
│   │   ├── bot/
│   │   │   ├── telegram_bot.py   # build_application(), handlers
│   │   │   └── replies.py        # format Verdict → simple multilingual message
│   │   ├── agent/                # the multi-phase LangGraph agent
│   │   │   ├── state.py          # GraphState TypedDict
│   │   │   ├── graph.py          # StateGraph wiring (the 6 phases)
│   │   │   ├── prompts.py        # Kimi system prompt
│   │   │   ├── llm.py            # make_llm() → TokenRouter/Kimi factory
│   │   │   ├── verdict.py        # Verdict Pydantic model (re-exported by schemas)
│   │   │   └── nodes/
│   │   │       ├── intake.py     # phase 1
│   │   │       ├── extract.py    # phase 3: ocr / transcribe / link_intel / passthrough
│   │   │       ├── analyze.py    # phase 4a
│   │   │       ├── verify.py     # phase 4b (ToolNode + tools)
│   │   │       ├── synthesize.py # phase 5
│   │   │       └── decide.py     # phase 6 routing
│   │   ├── integrations/         # one thin client per sponsor (swappable)
│   │   │   ├── sensenova.py
│   │   │   ├── whisper_stt.py
│   │   │   ├── videodb_stt.py
│   │   │   ├── brightdata.py
│   │   │   └── daytona.py
│   │   ├── services/             # business logic shared by ALL entry points
│   │   │   ├── check_service.py      # run agent on an input → Verdict (+ persist)
│   │   │   ├── guardian_service.py   # pairing codes, links
│   │   │   ├── alert_service.py      # fire family alert
│   │   │   └── intelligence_service.py
│   │   └── workers/              # optional ARQ worker
│   ├── scripts/
│   │   ├── gen_clients.sh    # openapi.json → TS (Hey API) + Dart (dart-dio)
│   │   ├── set_webhook.sh
│   │   └── seed.py
│   └── tests/
├── frontend/                 # placeholder (React/TS web dashboard)
│   └── README.md             # how to codegen client into src/client from /openapi.json
├── mobile/                   # placeholder (Flutter)
│   └── README.md             # how to codegen dart-dio client into lib/api
└── docs/
    └── openapi.json          # exported contract (generated)
```

**Key principle:** all three entry points (REST `/check`, Telegram webhook, future queue worker) call the **same**
`services/check_service.py`. The bot is just one client of the brain.

---

## 5. The multi-phase LangGraph agent

### State (shared, typed)
```python
# app/agent/state.py
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from app.agent.verdict import Verdict

Modality = Literal["text", "image", "voice", "link", "mixed"]

class GraphState(TypedDict):
    # inputs
    source: dict                     # {channel:"telegram", chat_id:..., user_id:...}
    raw_text: str                    # original text / caption
    image_bytes: Optional[bytes]
    audio_path: Optional[str]        # local path to converted audio (mp3/wav)
    urls: list[str]
    modality: Modality
    language_hint: Optional[str]
    # accumulated by extractors (reducers so parallel writes merge, never clobber)
    extracted_text: Annotated[list[str], lambda a, b: a + b]
    link_intel: Annotated[list[dict], lambda a, b: a + b]
    # the swarm
    messages: Annotated[list, add_messages]   # tool-calling loop for verify
    analysis: Optional[dict]                  # phase 4a intermediate
    verification: Optional[dict]              # phase 4b intermediate
    # output
    verdict: Optional[Verdict]
```
> **Gotcha (verified):** parallel branches writing the *same* state key raise `InvalidUpdateError` unless that key
> has a **reducer**. Hence `extracted_text` / `link_intel` use `a + b` reducers and `messages` uses `add_messages`.

### The six phases → nodes/edges
| Phase | Node(s) | What it does |
|---|---|---|
| 1. Intake | `intake` | Normalize input, set `modality`, detect `language_hint`. |
| 2. Route | `add_conditional_edges("intake", route_by_modality, {...})` | Fan out to extractor(s). Use `Send(...)` if a message carries multiple attachments. |
| 3. Extract | `ocr`, `transcribe`, `link_intel`, (`text`→straight) | Each writes into `extracted_text` / `link_intel`. Run in parallel. |
| 4. Analyze ∥ Verify | `analyze`, `verify` | **The swarm.** `analyze` = Kimi tactic detection; `verify` = `ToolNode` (link rep, brand-domain match, scam cross-ref). Both run, then merge. |
| 5. Synthesize | `synthesize` | `llm.with_structured_output(Verdict, method="json_schema")` → strict JSON in the user's language. |
| 6. Decide | `add_conditional_edges("synthesize", decide, {...})` | Always reply + persist; if `risk_level=="high"` → `alert_family`. |

### Wiring sketch
```python
# app/agent/graph.py
from langgraph.graph import StateGraph, START, END
from app.agent.state import GraphState
from app.agent.nodes import intake, extract, analyze, verify, synthesize, decide

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("intake", intake.run)
    g.add_node("ocr", extract.ocr)
    g.add_node("transcribe", extract.transcribe)
    g.add_node("link_intel", extract.link_intel)
    g.add_node("analyze", analyze.run)
    g.add_node("verify", verify.run)
    g.add_node("synthesize", synthesize.run)
    g.add_node("alert_family", decide.alert_family)

    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", extract.route_by_modality, {
        "image": "ocr", "voice": "transcribe", "link": "link_intel", "text": "analyze",
    })
    # extractors converge on the swarm
    for n in ("ocr", "transcribe", "link_intel"):
        g.add_edge(n, "analyze")
        g.add_edge(n, "verify")
    g.add_edge("text" if False else "analyze", "synthesize")  # analyze → synthesize
    g.add_edge("verify", "synthesize")
    g.add_conditional_edges("synthesize", decide.route, {
        "alert": "alert_family", "done": END,
    })
    g.add_edge("alert_family", END)
    return g.compile()   # add checkpointer=InMemorySaver() for replay/streaming
```
> Notes: `analyze` and `verify` both feed `synthesize`; LangGraph waits for both (a "super-step" join) before
> running `synthesize`. `route_by_modality` can return a **list of `Send(...)`** for mixed-modality messages so
> several extractors run in one parallel step.

### LLM factory (TokenRouter ↔ Kimi, env-flippable)
```python
# app/agent/llm.py
from langchain_openai import ChatOpenAI
from app.core.config import settings

def make_llm(role: str = "brain") -> ChatOpenAI:
    # role "triage" → cheap routing; "brain" → strong reasoning verdict
    model = settings.LLM_MODEL_TRIAGE if role == "triage" else settings.LLM_MODEL_BRAIN
    return ChatOpenAI(
        model=model,                       # e.g. "kimi-k2.6" direct, or "auto:cost" via TokenRouter
        base_url=settings.LLM_BASE_URL,    # api.moonshot.ai/v1  OR  api.tokenrouter.io/v1
        api_key=settings.LLM_API_KEY,
        temperature=0,
    )
```
> Default to **Kimi direct** for reliability; flip `LLM_BASE_URL`/`LLM_MODEL_*` to TokenRouter when a key is in hand.
> This satisfies the README's "Kimi is the brain" **and** "TokenRouter routes throughout" without code changes.
> If `kimi-k2.6` rejects `method="json_schema"`, drop `method=` to fall back to tool-calling structured output.

### System prompt
Keep the README's paste-ready Kimi prompt (§"The Kimi brain") verbatim in `app/agent/prompts.py`, with the JSON
schema extended to match the `Verdict` model in §6 (adds `scam_category`, `language`, `confidence`). The
`thinking` mode on k2.6 is on by default — disable it for the fast triage call to cut latency.

---

## 6. The shared contract: `Verdict` schema

This single Pydantic model is the heart of the contract — it flows through the agent, the API, the Telegram reply,
and (via OpenAPI codegen) into the TS and Dart clients.

```python
# app/agent/verdict.py
from typing import Literal, Optional
from pydantic import BaseModel, Field

class Verdict(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    is_scam: bool
    tactics: list[str] = Field(default_factory=list,
        description="named manipulation tactics detected; [] if none")
    explanation: str = Field(description="1–2 short sentences a 70-year-old understands, in the user's language")
    action: str = Field(description="the single clearest next step, in the user's language")
    alert_family: bool = Field(description="true only when risk_level == 'high'")
    # product/dashboard extensions:
    scam_category: Optional[str] = Field(default=None,
        description="e.g. bank_impersonation | govt_official | phishing | lottery | romance | job | other")
    language: str = Field(description="detected language code: en | zh | ms | ta")
    confidence: float = Field(ge=0, le=1)
```

---

## 7. Sponsor integrations (verified, with fallbacks)

> Each lives behind a thin client in `app/integrations/` so it can be swapped or stubbed. Confidence is from the
> June-2026 research sweep.

### Kimi k2.6 — the brain · **confidence: high**
- **Auth:** key from `platform.kimi.ai/console/api-keys` (the old `platform.moonshot.ai` redirects there). Env `MOONSHOT_API_KEY`. **No free tier** — min $1 recharge; $5 bonus at $5 cumulative. Hackathon alt: Kimi via **OpenRouter** credits.
- **Endpoint:** `https://api.moonshot.ai/v1` (global) / `https://api.moonshot.cn/v1` (China — separate account/key). OpenAI-compatible.
- **Model id:** `kimi-k2.6` (dot, not dash). Vision via `image_url` data-URI on k2.6.
- **Use:** phase-4 analyze + phase-5 synthesize (`response_format` json_schema), and **screenshot OCR fallback** (it's a vision model).
- **Gotcha:** verify the exact model string in the console; `thinking` mode default-on adds latency.

### SenseNova U1 — screenshot OCR + scam-of-week card · **confidence: medium**
- **Two paths:** (A) hosted OpenAI-compatible `https://token.sensenova.cn/v1` with an API key from `platform.sensenova.cn` (free beta ~1500 calls/model/5h); (B) **self-host** the Apache-2.0 open weights (`SenseNova/SenseNova-U1-8B-MoT`) via **vLLM-Omni** — no key, keeps user screenshots on our infra (privacy win for a scam product).
- **Use:** phase-3 `ocr` ("read all text verbatim, then judge"); **unique value = image generation** for the scam-of-week card (U1 unifies understanding + generation in one model).
- **⚠ Gotcha:** the exact **hosted model id** named "U1" could not be confirmed (`model="SenseNova-U1"` is a placeholder — read the real id from the console). **Fallback: Kimi-vision** for OCR. Treat SenseNova as the showcase + card generator with Kimi-vision behind a flag.

### VideoDB — voice transcription (sponsor path) · **confidence: medium**
- **SDK:** `pip install videodb` (0.4.5). `videodb.connect(api_key=...)` (env `VIDEO_DB_API_KEY`, **underscores around DB**) → `conn.upload(file_path=...)` → `audio.generate_transcript(language_code="zh")` → `audio.get_transcript_text()`. Free tier ~50 uploads.
- **⚠ Critical gotcha:** VideoDB transcription supports en/zh/ja/ko/hi/es/fr/de/ru but **NOT Malay (ms) or Tamil (ta)** — two of our four target languages. Also needs OGG→mp3 conversion (ffmpeg) first; audio objects use `generate_transcript`, **not** `index_spoken_words`.
- **Decision:** **Whisper is primary STT** (see §14). Keep VideoDB as the sponsor integration for English/Mandarin + its future video-indexing/search value, behind a flag.

### Whisper — primary STT · **confidence: high (fallback choice)**
- `faster-whisper` (local) or OpenAI Whisper API. Natively handles OGG/Opus and **all four** languages (en/zh/ms/ta) in one model. This is the reliability backbone for the elder voice differentiator.

### Bright Data — link/domain verification · **confidence: high**
- **Auth:** Bearer API token (`BRIGHTDATA_API_TOKEN`) + a **zone** created in the dashboard. ~5000 free req/month.
- **Endpoint:** single `POST https://api.brightdata.com/request` with `{zone, url, format}` — Web Unlocker (`format:"raw"`) and SERP (`format:"json"`) share it; zone decides behavior. SDK `pip install brightdata-sdk` or MCP server.
- **Use (compose, no single "is-scam" call):** (1) Unlocker-fetch a WHOIS page → **domain age**; (2) SERP the brand → canonical domain → **lookalike/homoglyph score**; (3) SERP `"<url>" scam OR phishing` → **this-week cross-ref**; (4) optional Unlocker-fetch the page for cloned-branding/fake-login signals.
- **⚠ Security:** fetched page HTML is **attacker-controlled** — never render/execute it, and sanitize before feeding to the LLM (prompt-injection risk).

### Daytona — safe link "detonation" sandbox · **confidence: high**
- **SDK:** `pip install daytona` (0.187.x). `Daytona(DaytonaConfig(api_key=...))` (env `DAYTONA_API_KEY`) → `daytona.create()` → `sandbox.process.exec("curl -sSIL --max-time 15 '<url>'")` → read `.result`/`.exit_code` → **`daytona.delete(sandbox)` in `finally`**. ~$200 starter credits + hackathon program credits.
- **Use:** when a link must actually be opened, do it in a disposable, network-isolated sandbox (resolve redirect chain, final URL, content-type) so nothing touches our host. One sandbox per URL.
- **Gotcha:** it's a general code sandbox, not a malware service — consider a cheap reputation API (urlscan.io / Google Safe Browsing) *first*, Daytona only for real detonation.

### TokenRouter — LLM gateway · **confidence: medium**
- **Endpoint:** `https://api.tokenrouter.io/v1` (OpenAI-compatible). Keys `tr_...` (env `TOKENROUTER_API_KEY`). Route modes via the `model` param: `auto:cost | auto:fast | auto:balance | auto:quality`, or pin a provider (`anthropic:...`, etc.).
- **⚠ Gotcha:** it's **BYO-key** — you add downstream provider keys in its console; it's a router, not a credit wallet. Credit availability for the hackathon is unconfirmed (ask the sponsor table). **Not** OpenRouter (`openrouter.ai`) — different product.
- **Use:** point `make_llm()` at it; `auto:cost` for triage, pin Kimi for the verdict. Console gives per-request cost/latency telemetry — nice for the demo.

---

## 8. Data model

```
users
  id (uuid, pk)
  telegram_chat_id (bigint, unique, nullable)   -- null for web/Flutter-only accounts
  name (text)
  language (text default 'en')                  -- en | zh | ms | ta
  role (text)                                   -- 'elder' | 'guardian' | 'both'
  created_at (timestamptz)

guardian_links
  id (uuid, pk)
  elder_id (fk users)
  guardian_id (fk users, nullable until claimed)
  pairing_code (text, unique)                   -- 6-char code, expires
  status (text)                                 -- 'pending' | 'active' | 'revoked'
  created_at (timestamptz)

reports                                          -- one per checked item; feeds the intelligence product
  id (uuid, pk)
  user_id (fk users, nullable)
  channel (text)                                -- 'telegram' | 'web' | 'mobile'
  modality (text)                               -- text | image | voice | link | mixed
  raw_text (text)
  extracted_text (text)
  source_url (text, nullable)
  risk_level (text)                             -- high | medium | low
  is_scam (bool)
  scam_category (text)
  tactics (jsonb)                               -- list[str]
  language (text)
  confidence (real)
  verdict (jsonb)                               -- full Verdict for audit
  created_at (timestamptz, indexed)             -- for trend windows

link_intel_cache  (optional, dedupe Bright Data cost)
  domain (text, pk)
  domain_age_days (int)
  lookalike_score (real)
  scam_mentions (int)
  fetched_at (timestamptz)

scam_of_week
  id (uuid, pk)
  week (date)
  title (text)
  body (text)
  image_url (text)                              -- SenseNova-generated card
  language (text)
```

Anonymized aggregates over `reports` (by `scam_category`, `risk_level`, `created_at` window) = the **scam-intelligence
feed** / dashboard data product.

---

## 9. API surface

All under `/api/v1` except the bot webhook and health. FastAPI auto-serves `/openapi.json`, `/docs`, `/redoc`.

| Method & path | Purpose | Consumers |
|---|---|---|
| `POST /telegram/webhook` | Telegram updates (verify secret header; ack fast; agent in BackgroundTask). `include_in_schema=False`. | Telegram |
| `POST /api/v1/check` | **Core.** `multipart/form-data`: optional `text`, `image` file, `audio` file, `url`. Runs the agent, returns `Verdict` + `report_id`. Synchronous (fine for direct API callers). | web, Flutter, manual test |
| `GET /api/v1/reports` | Paginated history for the authed user. | web, Flutter |
| `GET /api/v1/reports/{id}` | Single report + full verdict. | web, Flutter |
| `POST /api/v1/guardians/invite` | Elder generates a pairing code. | web, Flutter, bot |
| `POST /api/v1/guardians/link` | Guardian claims a pairing code. | web, Flutter, bot |
| `GET /api/v1/guardians` | List my linked elders/guardians. | web, Flutter |
| `GET /api/v1/intelligence/trends` | Aggregated trending scams (windowed). **B2B data product.** | dashboard |
| `GET /api/v1/intelligence/stats` | Counts by category/risk/time. | dashboard |
| `GET /api/v1/alerts/stream` | (optional) SSE/WebSocket realtime high-risk alerts. | dashboard |
| `GET /health` | Liveness. | infra |

**Async option:** if a client wants non-blocking checks, add `POST /api/v1/check` → returns `{report_id, status:"processing"}`
immediately and `GET /api/v1/reports/{id}` to poll. For the hackathon, synchronous `/check` is simplest; Telegram is the
only path that *must* be async (webhook retry constraint).

---

## 10. Telegram bot design

- **Setup:** `@BotFather` → `/newbot` → `TELEGRAM_BOT_TOKEN`. Set `/setcommands`, `/setdescription` for polish.
- **Webhook:** in FastAPI `lifespan`, build the PTB `Application` with `.updater(None)`, `await app.initialize()`,
  `await bot.set_webhook(url, secret_token=WEBHOOK_SECRET, allowed_updates=ALL_TYPES)`. The `/telegram/webhook` handler
  verifies `X-Telegram-Bot-Api-Secret-Token`, parses `Update.de_json`, then **`process_update`**. **Return 200 fast**;
  run the agent in a BackgroundTask, then push the result with `bot.send_message`.
- **Intake mapping:**
  - text → `message.text`
  - screenshot → `message.photo[-1]` (largest) → `bot.get_file` → download → SenseNova/Kimi-vision
  - voice → `message.voice` (OGG/Opus) → download → ffmpeg → Whisper/VideoDB (also handle `message.audio`/`document`)
  - link → URL entities: `type=="url"` (slice by offset/length) or `type=="text_link"` (`entity.url`); captions use `caption_entities`
- **Guardian pairing (works around the "must /start first" rule):**
  1. Elder sends `/invite` → bot returns a 6-char code (row in `guardian_links`, status `pending`).
  2. Guardian **starts the bot** (`/start`) then sends `/guardian <code>` → we capture the guardian's `chat_id`, link the pair, status `active`.
- **Family alert:** on `risk_level=="high"`, `alert_service` calls `bot.send_message(guardian_chat_id, "<elder> is being targeted by a scam right now")`.
- **Scam of the week:** PTB `JobQueue.run_daily/run_repeating` (or the `mcp__scheduled-tasks` cron) iterates subscribed `chat_id`s and sends the SenseNova card + one-liner.
- **Replies:** `bot/replies.py` renders the `Verdict` into a calm, simple message in `verdict.language`, with a 🔴/🟡/🟢 prefix and the named tactic.

---

## 11. Web + Flutter readiness (OpenAPI codegen)

The backend is the single source of truth; both clients are **generated**, never hand-written, so the contract can't drift.

- **Stable method names:** set `FastAPI(generate_unique_id_function=...)` so `operationId`s are short/stable
  (e.g. `check_create`, `reports_list`) — otherwise codegen produces ugly names that churn on every rename.
- **Web (React/TS):** Hey API (FastAPI's recommended tool):
  ```bash
  npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o frontend/src/client
  ```
- **Flutter (Dart):** OpenAPI Generator `dart-dio` (Dio + json_serializable/built_value):
  ```bash
  npx @openapitools/openapi-generator-cli generate -g dart-dio \
    -i http://localhost:8000/openapi.json -o mobile/lib/api
  ```
- `scripts/gen_clients.sh` does both from a running server. `frontend/` and `mobile/` are stub folders with READMEs now;
  no app code this phase.
- **CORS:** explicit origins (web dev `http://localhost:5173`, deployed URL); never `allow_origins=["*"]` with credentials.

---

## 12. Configuration & secrets (`.env`)

`backend/.env.example` (committed; real `.env` is gitignored). Loaded via `pydantic-settings`.

```dotenv
# --- App ---
ENV=dev
CORS_ORIGINS=["http://localhost:5173"]

# --- Database (Supabase) ---
# runtime: pooled (6543); asyncpg needs statement cache disabled (see db.py)
DATABASE_URL=postgresql+asyncpg://postgres:<pw>@<host>:6543/postgres
# migrations only: direct (5432)
DATABASE_URL_DIRECT=postgresql+asyncpg://postgres:<pw>@<host>:5432/postgres

# --- Telegram ---
TELEGRAM_BOT_TOKEN=123456789:AAH...           # @BotFather
WEBHOOK_BASE_URL=https://<your>.trycloudflare.com
WEBHOOK_SECRET=<random-string>

# --- LLM (pick ONE base_url; flip to TokenRouter when available) ---
LLM_BASE_URL=https://api.moonshot.ai/v1       # or https://api.tokenrouter.io/v1
LLM_API_KEY=sk-...                            # MOONSHOT key, or tr_... for TokenRouter
LLM_MODEL_BRAIN=kimi-k2.6                      # or e.g. auto:quality via TokenRouter
LLM_MODEL_TRIAGE=kimi-k2.6                     # or auto:cost via TokenRouter

# --- Sponsors ---
SENSENOVA_API_KEY=                             # token.sensenova.cn  (or self-host → leave blank)
SENSENOVA_BASE_URL=https://token.sensenova.cn/v1
VIDEO_DB_API_KEY=                              # note: underscores around DB
BRIGHTDATA_API_TOKEN=
BRIGHTDATA_SERP_ZONE=serp_api1
BRIGHTDATA_UNLOCKER_ZONE=unblocker
DAYTONA_API_KEY=

# --- STT ---
STT_PROVIDER=whisper                           # whisper | videodb
```

---

## 13. Milestones / build order

Backend-first, riskiest-thing-first within each step. Each milestone ends with a verifiable check.

- **M0 — Scaffold.** `pyproject.toml`, FastAPI app, `/health`, `config.py`, `db.py`, Supabase connection (with the
  asyncpg `statement_cache_size=0` fix), Alembic init, base tables. ✅ `GET /health` returns ok; tables migrated.
- **M1 — The brain (highest priority).** `agent/` graph for **text-only**: intake → analyze → synthesize → strict
  `Verdict`. Wire `make_llm()` to Kimi. ✅ `POST /api/v1/check` with text returns a correct multilingual Verdict.
  *Don't move on until this is reliable.*
- **M2 — Telegram round-trip.** Bot token, cloudflared tunnel, webhook in lifespan, text handler → `check_service` →
  reply. ✅ A judge texts the bot and gets a verdict.
- **M3 — Screenshots.** `ocr` node: SenseNova U1 (Kimi-vision fallback) → pipeline. ✅ Forwarded image → verdict.
- **M4 — Links.** `link_intel` node: Bright Data WHOIS-age + brand-lookalike + scam cross-ref; optional Daytona
  safe-open; `verify` ToolNode consumes it. ✅ Suspicious URL → verdict cites domain age/impersonation.
- **M5 — Voice.** `transcribe` node: Whisper primary (VideoDB flag). ffmpeg OGG→mp3. ✅ Voice note → transcript → verdict.
- **M6 — Family loop.** `guardian_links`, `/invite` + `/guardian <code>`, `alert_service` fires on high risk. ✅ High-risk
  case pings the guardian's phone.
- **M7 — Intelligence API.** `intelligence/trends` + `stats` aggregations over `reports`. ✅ Endpoint returns trending
  scams; this is the dashboard's data source.
- **M8 — Contract export & client stubs.** `generate_unique_id_function`, export `docs/openapi.json`, prove
  `gen_clients.sh` produces TS + Dart clients. ✅ Both clients generate cleanly.
- **M9 — Polish & demo.** `/setcommands`, scam-of-week job, seed demo data, README for run steps.

---

## 14. De-risking & key decisions

1. **Voice STT: Whisper primary, VideoDB optional.** VideoDB transcription does **not** support Malay or Tamil — half
   our target languages. `faster-whisper` covers all four and ingests OGG natively. We still wire VideoDB behind
   `STT_PROVIDER=videodb` so the sponsor is integrated and demoable on English/Mandarin, but the reliable demo path is
   Whisper. (Voice was already flagged the riskiest piece in the README.)
2. **SenseNova hosted model id is unconfirmed.** We code against `SENSENOVA_BASE_URL` + a configurable model id and ship
   **Kimi-vision as the OCR fallback**, so a screenshot demo never depends on resolving the exact `U1` hosted id.
   SenseNova's defensible, unique role = generating the scam-of-week **card image**.
3. **Kimi has no free API tier.** Budget a small recharge, or get Kimi via **OpenRouter**/TokenRouter sponsor credits.
   The `make_llm()` factory means the provider is one env change.
4. **Daytona vs. reputation APIs.** Daytona is isolation, not a verdict. Cheap reputation lookups (urlscan / Google Safe
   Browsing) can be the first pass; Daytona is reserved for genuinely opening a link safely. Optional for the demo.
5. **Never run the agent inline in the Telegram webhook.** Telegram retries slow webhooks → double-processing. Ack 200
   immediately, run in BackgroundTask, push via `bot.send_message`.
6. **Supabase + asyncpg footgun.** Pooled (6543) connection breaks asyncpg prepared statements; set
   `connect_args={"statement_cache_size":0, "prepared_statement_cache_size":0}`. Use direct (5432) for Alembic only.
7. **Treat fetched scam-page HTML as hostile.** Sandbox the fetch (Bright Data Unlocker / Daytona) and sanitize before
   any LLM sees it — prompt-injection risk.

---

## 15. Local dev & run

```bash
# backend
cd backend
python -m venv .venv && . .venv/Scripts/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .                                         # from pyproject
cp .env.example .env                                     # fill in secrets
alembic upgrade head                                     # uses DATABASE_URL_DIRECT
uvicorn app.main:app --reload                            # http://localhost:8000/docs

# public HTTPS for the Telegram webhook (separate terminal)
cloudflared tunnel --url http://localhost:8000
# put the printed https URL into WEBHOOK_BASE_URL, restart uvicorn (lifespan re-runs set_webhook)
```

Prereqs: Python 3.12+, **ffmpeg** on PATH (voice conversion), a Supabase project, a Telegram bot token, cloudflared.

---

## 16. Success criteria (Telegram, backend)

- [ ] A judge can text the **Telegram bot** and get a correct, simple verdict live.
- [ ] At least three input types work end-to-end (text, screenshot, voice).
- [ ] The verdict names the **tactic** in plain language, in more than one language (en + zh minimum).
- [ ] The **family alert** fires to the guardian on a high-risk case.
- [ ] `GET /api/v1/intelligence/trends` returns aggregated trending scams (dashboard data product).
- [ ] At least three sponsors integrated meaningfully (Kimi + SenseNova + Bright Data minimum; Daytona/VideoDB/TokenRouter as reach).
- [ ] `/openapi.json` exported and both TS + Dart clients generate cleanly (proves web + Flutter readiness).

---

## 17. Open questions / assumptions

**Assumptions made (say the word to change any):**
- Backend language = **Python** (LangGraph-driven). Web later = React/TS; mobile = Flutter.
- DB = **Supabase Postgres** (its MCP is already connected here); SQLite is the offline fallback.
- LLM default = **Kimi direct**, with TokenRouter as the flip-on gateway.
- This phase delivers **no frontend code** — only the contract + stub folders + codegen scripts.
- README stays the pitch doc; **PLAN.md is authoritative** where they differ (channel = Telegram).

**Need confirmation:**
- Which sponsors are *required* to be integrated for judging vs. nice-to-have? (Affects M3–M5 priority.)
- Auth model for the web/Flutter REST API: Supabase Auth JWTs, or our own JWT? (M-later; bot needs none.)
- Hosting for the demo: keep local + cloudflared, or a paid Render/Railway window?
