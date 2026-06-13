# 🛡️ Scam Guardian — Build Plan (Demo-first, SQLite, Telegram, multi-phase LangGraph agent)

> This is the **authoritative technical plan**. [README.md](README.md) is the product/market pitch and stays as-is.
> Where the README says **WhatsApp**, we build on **Telegram** instead (rationale in §1). The business model, market,
> and demo narrative in the README are channel-agnostic and still hold.

**Scope:** build a **working demo backend** — no production hardening. The scam-detection "brain" is a
**multi-phase agent built on LangChain + LangGraph**. Storage is **SQLite** (a single local file). Two input
channels feed the same brain:
1. **Reactive** — a user *forwards* a suspicious text / screenshot / voice note / link to the Telegram bot.
2. **Autonomous** — the system *watches an email inbox* and, when a scam email arrives, **automatically alerts the
   linked family members** through the bot. No forwarding needed.

Everything is designed so a **web app (React/TS)** and a **Flutter (Dart) mobile app** can be added later with zero
backend rework — but **no frontend code is built this phase.**

---

## Table of contents
1. [What changed vs. the README](#1-what-changed-vs-the-readme)
2. [Architecture (updated)](#2-architecture-updated)
3. [Tech stack & why](#3-tech-stack--why)
4. [Repository layout](#4-repository-layout)
5. [The multi-phase LangGraph agent](#5-the-multi-phase-langgraph-agent)
6. [The shared contract: Verdict schema](#6-the-shared-contract-verdict-schema)
7. [Autonomous email monitoring → family alert](#7-autonomous-email-monitoring--family-alert)
8. [Sponsor integrations (verified, with fallbacks)](#8-sponsor-integrations-verified-with-fallbacks)
9. [Data model (SQLite)](#9-data-model-sqlite)
10. [API surface](#10-api-surface)
11. [Telegram bot design (long polling)](#11-telegram-bot-design-long-polling)
12. [Web + Flutter readiness (OpenAPI codegen)](#12-web--flutter-readiness-openapi-codegen)
13. [Configuration & secrets (.env)](#13-configuration--secrets-env)
14. [Milestones / build order](#14-milestones--build-order)
15. [De-risking & key decisions](#15-de-risking--key-decisions)
16. [Local dev & run](#16-local-dev--run)
17. [Success criteria](#17-success-criteria)
18. [Open questions / assumptions](#18-open-questions--assumptions)

---

## 1. What changed vs. the README

| README says | This plan does | Why |
|---|---|---|
| WhatsApp via Twilio | **Telegram bot** (long polling) | Free, instant `@BotFather` setup; native text/photo/voice/link; can proactively message family; **long polling needs no public URL/tunnel** — ideal for a demo. |
| "Kimi agent swarm" | **LangGraph state machine** with parallel `analyze ∥ verify` | The swarm as an explicit, debuggable graph. "Multi-phase using LangChain" = LangGraph. |
| Only reactive (user forwards) | **+ Autonomous email monitoring** | New: watch an inbox; on a scam email, auto-alert the family — even if the elder never forwards it. (§7) |
| Production data product | **SQLite, demo-only** | One local file, zero infra. No Supabase/Postgres/Alembic/Redis/tunnel. We keep the *trends* idea as simple aggregate queries over the SQLite `reports` table. |
| One-day full stack | **Backend-first**, contract-driven | Web + Flutter consume the same OpenAPI contract later; no frontend code now. |

**Deliberately NOT used** (per "don't use it if there's no need"): Postgres/Supabase, Alembic migrations, Redis/ARQ
queue, cloudflared/ngrok tunnel, Telegram webhooks. All are noted as the production upgrade path but excluded from the
demo build.

---

## 2. Architecture (updated)

```
 ┌─ CHANNEL A: Telegram (reactive) ─────────┐     ┌─ CHANNEL B: Email inbox (autonomous) ─┐
 │  user forwards text/photo/voice/link     │     │  a new email arrives in the inbox      │
 └──────────────┬───────────────────────────┘     └──────────────────┬─────────────────────┘
                │ bot (LONG POLLING — no tunnel)                       │ IMAP poller (~every 20s)
                │                                                      │
                ▼                                                      ▼
   ┌──────────────────────── LangGraph multi-phase agent (one brain) ────────────────────────┐
   │  1 intake/normalize  → modality + language                                               │
   │  2 route (cond. edge)                                                                     │
   │  3 extract (parallel): image→SenseNova U1 (Kimi-vision fallback) · voice→Whisper(/VideoDB)│
   │                        · link→Bright Data (+Daytona safe-open) · text/email→passthrough   │
   │  4 analyze ∥ verify  (the swarm): Kimi k2.6 tactic detection  +  tool verification        │
   │  5 synthesize        → strict Verdict JSON, in the user's language                        │
   │  6 decide            → reply / save / alert family                                        │
   └────────────────────────────────────────────────────────────────────────────────────────┘
                │                          │                              │
                ▼                          ▼                              ▼
        reply to the user          save to SQLite               if scam → alert FAMILY via bot
        (Telegram only)            (reports → trends)            • forwarded high-risk item, OR
                                                                 • scam EMAIL: "📧 Mum's inbox got
                                                                   a scam email from <sender> …"

   (Web + Flutter later call the SAME brain via  POST /api/v1/check.  All LLM calls go through
    make_llm() → Kimi direct by default, TokenRouter by env flip.)
```

---

## 3. Tech stack & why

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.12+** | LangGraph is Python-first; pairs with FastAPI. |
| Web framework | **FastAPI** + Uvicorn | Async; auto **OpenAPI 3.1** = the shared contract for web + Flutter. |
| Schemas | **Pydantic v2** | Request/response + the `Verdict` contract. |
| Agent engine | **LangGraph 1.2.x** (`langgraph>=1.2,<2`) + `langchain>=1.3,<2` + `langchain-openai>=1.2,<2` | StateGraph, conditional edges, `Send` fan-out, `ToolNode`, `with_structured_output`. |
| LLM "brain" | **Kimi k2.6** (Moonshot), OpenAI-compatible | `base_url=https://api.moonshot.ai/v1`, model `kimi-k2.6` (**dot, not dash**), 256K ctx, vision + json output. |
| LLM gateway | **TokenRouter** (optional, OpenAI-compatible) | Env-flip to `https://api.tokenrouter.io/v1` for cost routing; off by default. |
| **Storage** | **SQLite** via **SQLModel** (+ `aiosqlite` for async) | Single file `scamguardian.db`. Tables created on startup with `SQLModel.metadata.create_all` — **no Alembic.** |
| Telegram | **python-telegram-bot v22** (`[job-queue]`) | **Long polling** inside FastAPI lifespan — no webhook, no public URL. |
| Email intake | **IMAP** via `imaplib` (stdlib) or `aioimaplib` | Poll an inbox for new mail; IMAP IDLE is the optional "instant" upgrade. |
| STT | **faster-whisper** (primary) / **VideoDB** (sponsor path) | VideoDB lacks Malay & Tamil — see §15. |
| Screenshot OCR | **SenseNova U1** (sponsor) / **Kimi-vision** (fallback) | SenseNova also generates the scam-of-week card. |
| Link intel | **Bright Data** + **Daytona** (optional) | Domain age + brand-lookalike + this-week cross-ref. |
| Slow work | run the agent in a PTB handler / asyncio task | No queue. Long polling has no retry-storm problem, so inline is fine for a demo. |

---

## 4. Repository layout

```
ai-agent-hackathon/
├── README.md                 # product/market pitch (unchanged)
├── PLAN.md                   # this file
├── PLAN-SIMPLE.md            # plain-English version
├── .gitignore
├── backend/                  # ← all work this phase
│   ├── pyproject.toml
│   ├── .env.example
│   ├── scamguardian.db       # SQLite file (gitignored)
│   ├── app/
│   │   ├── main.py           # FastAPI app + lifespan (create tables, start bot polling, start email poller), CORS
│   │   ├── core/
│   │   │   ├── config.py     # pydantic-settings BaseSettings
│   │   │   └── db.py         # async SQLite engine + get_session() + init_db()
│   │   ├── models/           # SQLModel table=True models
│   │   ├── schemas/          # Pydantic v2 request/response (incl. Verdict) = the CONTRACT
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routers/
│   │   │       ├── check.py        # POST /api/v1/check  (core, reused by all clients)
│   │   │       ├── reports.py      # report history
│   │   │       ├── guardians.py    # pairing / family loop
│   │   │       ├── email_accounts.py  # link an inbox to an elder (optional; .env works for demo)
│   │   │       └── intelligence.py # trends (simple SQLite aggregates)
│   │   ├── bot/
│   │   │   ├── telegram_bot.py   # build_application(), handlers (forwarded items + /commands)
│   │   │   └── replies.py        # format Verdict → simple multilingual message
│   │   ├── ingest/
│   │   │   └── email_monitor.py  # IMAP poll loop → check_service → alert (CHANNEL B)
│   │   ├── agent/
│   │   │   ├── state.py          # GraphState TypedDict
│   │   │   ├── graph.py          # StateGraph wiring (the 6 phases)
│   │   │   ├── prompts.py        # Kimi system prompt
│   │   │   ├── llm.py            # make_llm() → Kimi / TokenRouter factory
│   │   │   ├── verdict.py        # Verdict Pydantic model
│   │   │   └── nodes/            # intake, extract, analyze, verify, synthesize, decide
│   │   ├── integrations/         # one thin client per sponsor (swappable)
│   │   │   ├── sensenova.py · whisper_stt.py · videodb_stt.py · brightdata.py · daytona.py
│   │   └── services/             # business logic shared by ALL entry points
│   │       ├── check_service.py      # run agent on an input → Verdict (+ persist)
│   │       ├── guardian_service.py   # pairing codes, links
│   │       ├── alert_service.py      # fire family alert (used by forwarded high-risk AND scam emails)
│   │       └── intelligence_service.py
│   ├── scripts/  (gen_clients.sh · seed.py)
│   └── tests/
├── frontend/   README.md     # placeholder: codegen TS client into src/client from /openapi.json
├── mobile/     README.md     # placeholder: codegen dart-dio client into lib/api
└── docs/openapi.json         # exported contract (generated)
```

**Key principle:** every entry point (Telegram forward, email poller, REST `/check`) calls the **same**
`services/check_service.py` and `services/alert_service.py`. One brain, one alert path.

---

## 5. The multi-phase LangGraph agent

### State (shared, typed)
```python
# app/agent/state.py
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from app.agent.verdict import Verdict

Modality = Literal["text", "image", "voice", "link", "email", "mixed"]

class GraphState(TypedDict):
    source: dict                     # {channel:"telegram"|"email"|"web", who:..., sender:...}
    raw_text: str                    # text / email body / caption
    image_bytes: Optional[bytes]
    audio_path: Optional[str]        # local path to converted audio
    urls: list[str]
    modality: Modality
    language_hint: Optional[str]
    # accumulated by parallel extractors → reducers so concurrent writes MERGE (don't clobber)
    extracted_text: Annotated[list[str], lambda a, b: a + b]
    link_intel: Annotated[list[dict], lambda a, b: a + b]
    messages: Annotated[list, add_messages]   # tool-calling loop for verify
    analysis: Optional[dict]
    verification: Optional[dict]
    verdict: Optional[Verdict]
```
> **Gotcha (verified):** parallel branches writing the same key raise `InvalidUpdateError` without a reducer — hence
> the `a + b` reducers and `add_messages`.

### The six phases
| Phase | Node(s) | What it does |
|---|---|---|
| 1 Intake | `intake` | Normalize input; set `modality`; detect language. Email = body text + urls (+ optional attachment image). |
| 2 Route | `add_conditional_edges("intake", route_by_modality, {...})` | Fan out by modality (`Send` for multi-attachment). |
| 3 Extract | `ocr`, `transcribe`, `link_intel`, text/email→straight | Each writes `extracted_text` / `link_intel`; parallel. |
| 4 Analyze ∥ Verify | `analyze`, `verify` | The swarm: Kimi tactic detection + `ToolNode` checks. Both join at synthesize. |
| 5 Synthesize | `synthesize` | `llm.with_structured_output(Verdict, method="json_schema")` → strict JSON in the user's language. |
| 6 Decide | `add_conditional_edges("synthesize", decide, {...})` | Always persist; reply (Telegram) or alert family (high-risk / scam email). |

### Wiring sketch
```python
# app/agent/graph.py
from langgraph.graph import StateGraph, START, END
from app.agent.state import GraphState
from app.agent.nodes import intake, extract, analyze, verify, synthesize, decide

def build_graph():
    g = StateGraph(GraphState)
    for name, fn in [("intake", intake.run), ("ocr", extract.ocr), ("transcribe", extract.transcribe),
                     ("link_intel", extract.link_intel), ("analyze", analyze.run), ("verify", verify.run),
                     ("synthesize", synthesize.run), ("alert_family", decide.alert_family)]:
        g.add_node(name, fn)
    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", extract.route_by_modality,
                            {"image": "ocr", "voice": "transcribe", "link": "link_intel", "text": "analyze"})
    for n in ("ocr", "transcribe", "link_intel"):
        g.add_edge(n, "analyze"); g.add_edge(n, "verify")
    g.add_edge("analyze", "synthesize"); g.add_edge("verify", "synthesize")
    g.add_conditional_edges("synthesize", decide.route, {"alert": "alert_family", "done": END})
    g.add_edge("alert_family", END)
    return g.compile()
```

### LLM factory (Kimi by default, TokenRouter by env flip)
```python
# app/agent/llm.py
from langchain_openai import ChatOpenAI
from app.core.config import settings

def make_llm(role: str = "brain") -> ChatOpenAI:
    model = settings.LLM_MODEL_TRIAGE if role == "triage" else settings.LLM_MODEL_BRAIN
    return ChatOpenAI(model=model, base_url=settings.LLM_BASE_URL,
                      api_key=settings.LLM_API_KEY, temperature=0)
```
> If `kimi-k2.6` rejects `method="json_schema"`, drop `method=` to fall back to tool-calling structured output.

### System prompt
Use the README's paste-ready Kimi prompt in `app/agent/prompts.py`, with the JSON schema extended to the `Verdict`
model in §6. Disable k2.6 `thinking` mode for the fast path to cut latency.

---

## 6. The shared contract: `Verdict` schema

```python
# app/agent/verdict.py
from typing import Literal, Optional
from pydantic import BaseModel, Field

class Verdict(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    is_scam: bool
    tactics: list[str] = Field(default_factory=list, description="named tactics; [] if none")
    explanation: str = Field(description="1–2 simple sentences in the user's language")
    action: str = Field(description="the single clearest next step, in the user's language")
    alert_family: bool = Field(description="true when risk_level == 'high'")
    scam_category: Optional[str] = Field(default=None,
        description="bank_impersonation | govt_official | phishing | lottery | romance | job | other")
    language: str = Field(description="en | zh | ms | ta")
    confidence: float = Field(ge=0, le=1)
```
This one model flows through the agent, the API, the Telegram reply, the email alert, and (via OpenAPI codegen) into
the TS and Dart clients.

---

## 7. Autonomous email monitoring → family alert

**The new feature.** Instead of waiting for the elder to forward something, Scam Guardian *watches their inbox* and
alerts the family the moment a scam email arrives.

### Flow
```
new email in inbox  →  IMAP poller fetches it  →  parse sender/subject/body/urls
   →  check_service runs the SAME agent  →  Verdict
   →  if is_scam and risk_level == "high":
        look up inbox owner (elder)  →  their linked guardians (guardian_links)
        →  bot.send_message(each guardian):
           "📧 Scam email alert — <Elder>'s inbox just received an email from
            '<sender>' that looks like a scam (<tactic>). Please check on them
            and tell them not to click anything or reply."
   →  save a report row (channel='email') for the trends data
```

### How "an email reached the inbox" is detected (demo-simple)
- Configure **one monitored inbox** in `.env` (Gmail + an **App Password**, IMAP enabled).
- A background `asyncio` task started in the FastAPI lifespan **polls IMAP every ~20s** for `UNSEEN` messages
  (`imaplib` in a thread, or `aioimaplib`). For each new message: parse with the stdlib `email` module, strip HTML to
  plain text, extract URLs, run the agent, alert if scam, mark seen / track last UID.
- **Optional upgrade:** IMAP **IDLE** for near-instant push, or a provider webhook (SendGrid Inbound Parse) — out of
  scope for the demo.

### Minimal poller sketch
```python
# app/ingest/email_monitor.py  (simplified)
import imaplib, email, asyncio
from email.header import make_header, decode_header
from app.core.config import settings
from app.services.check_service import check_email
from app.services.alert_service import alert_family_scam_email

async def run_email_monitor():
    while True:
        try:
            await asyncio.to_thread(_poll_once)
        except Exception as e:
            ...  # log, keep looping
        await asyncio.sleep(settings.EMAIL_POLL_SECONDS)

def _poll_once():
    m = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST)
    m.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
    m.select("INBOX")
    _, data = m.search(None, "UNSEEN")
    for num in data[0].split():
        _, raw = m.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(raw[0][1])
        sender = str(make_header(decode_header(msg.get("From", ""))))
        subject = str(make_header(decode_header(msg.get("Subject", ""))))
        body = _plaintext_body(msg)          # strip HTML, treat as UNTRUSTED
        verdict = check_email(sender, subject, body)   # → runs the agent, persists report
        if verdict.is_scam and verdict.risk_level == "high":
            alert_family_scam_email(inbox=settings.EMAIL_IMAP_USER,
                                    sender=sender, verdict=verdict)
        m.store(num, "+FLAGS", "\\Seen")
    m.logout()
```

### Who gets alerted
Reuses **`guardian_links`**: the monitored inbox maps to an **elder** (via `email_accounts`, or a single mapping in
`.env` for the demo); that elder's **active guardians** receive the Telegram alert. "Selected family members" = the
guardians linked to that elder. (Optionally also notify the elder if they're a bot user.)

### Safety
Email HTML is attacker-controlled → **strip to plain text and sanitize before the LLM sees it** (prompt-injection
risk), exactly like fetched web pages. Never auto-open links from the email except inside Daytona/Bright Data.

---

## 8. Sponsor integrations (verified, with fallbacks)

> Each lives behind a thin client in `app/integrations/`, so any can be stubbed. Tiers: 🟢 load-bearing, 🟡 showcase
> (has a fallback). Confidence is from the June-2026 research sweep.

### Kimi k2.6 — the brain · 🟢 · confidence: high
- **Auth:** key from `platform.kimi.ai/console/api-keys` (old `platform.moonshot.ai` redirects there). Env `MOONSHOT_API_KEY`. **No free tier** (min $1 recharge); hackathon alt: Kimi via **OpenRouter**/TokenRouter credits.
- **Endpoint:** `https://api.moonshot.ai/v1` (global) / `.cn` (China, separate key). OpenAI-compatible. Model `kimi-k2.6` (dot). Vision via `image_url` data-URI.
- **Use:** phase-4 analyze + phase-5 synthesize (json output); screenshot OCR fallback.

### Bright Data — link/domain verification · 🟢 · confidence: high
- **Auth:** Bearer `BRIGHTDATA_API_TOKEN` + a **zone** created in the dashboard. ~5000 free req/month.
- **Endpoint:** `POST https://api.brightdata.com/request` with `{zone, url, format}` (Web Unlocker `raw` / SERP `json`).
- **Use (compose):** Unlocker-fetch a WHOIS page → domain age; SERP brand → canonical domain → lookalike score; SERP `"<url>" scam` → this-week cross-ref. **Treat fetched HTML as hostile.**

### SenseNova U1 — screenshot OCR + scam-of-week card · 🟡 (fallback: Kimi-vision) · confidence: medium
- Hosted OpenAI-compatible `https://token.sensenova.cn/v1` (free beta ~1500 calls/model/5h) **or** self-host Apache-2.0 weights (`SenseNova/SenseNova-U1-8B-MoT`) via vLLM-Omni.
- **⚠** exact hosted "U1" model id unconfirmed → keep `SENSENOVA_BASE_URL` + model configurable; **Kimi-vision** is the OCR fallback. Unique value = generating the scam-of-week **card image**.

### VideoDB — voice transcription · 🟡 (fallback/primary: Whisper) · confidence: medium
- `pip install videodb`; `connect → upload(file_path) → audio.generate_transcript(language_code) → get_transcript_text()`. Env `VIDEO_DB_API_KEY` (underscores around DB). Needs OGG→mp3 (ffmpeg).
- **⚠ no Malay/Tamil** → **Whisper is the primary STT** (§15). VideoDB stays for EN/ZH + future video search.

### Whisper — primary STT · confidence: high
- `faster-whisper` (local) or Whisper API. Handles OGG/Opus and **all four** languages in one model.

### Daytona — safe link sandbox · 🟡 (optional) · confidence: high
- `pip install daytona`; `Daytona(DaytonaConfig(api_key=...))` → `create()` → `sandbox.process.exec("curl -sSIL …")` → **`delete()` in `finally`**. Env `DAYTONA_API_KEY`. ~$200 starter + hackathon credits.
- General sandbox, not a verdict — a cheap reputation API (urlscan/Safe Browsing) can come first; Daytona for real safe-open.

### TokenRouter — LLM gateway · 🟡 (off by default) · confidence: medium
- `https://api.tokenrouter.io/v1` (OpenAI-compatible), keys `tr_…`, modes `auto:cost|fast|balance|quality`. **BYO provider keys** in its console — it's a router, not a wallet; hackathon credits unconfirmed. Not OpenRouter. Flip on via `make_llm()` env.

---

## 9. Data model (SQLite)

SQLModel tables, created on startup (`SQLModel.metadata.create_all`). No migrations.

```
users
  id INTEGER pk · telegram_chat_id INTEGER (unique, nullable) · name TEXT
  language TEXT default 'en' · role TEXT ('elder'|'guardian'|'both') · created_at TEXT

guardian_links
  id INTEGER pk · elder_id INTEGER fk · guardian_id INTEGER fk (nullable until claimed)
  pairing_code TEXT (unique) · status TEXT ('pending'|'active'|'revoked') · created_at TEXT

email_accounts                          -- maps a monitored inbox → an elder (CHANNEL B)
  id INTEGER pk · elder_id INTEGER fk · email_address TEXT (unique)
  imap_host TEXT · active INTEGER (bool)
  -- demo: a single inbox can instead be set in .env; this table is the multi-user path

reports                                  -- one per checked item; feeds the trends product
  id INTEGER pk · user_id INTEGER fk (nullable) · channel TEXT ('telegram'|'email'|'web')
  modality TEXT · sender TEXT (nullable, email) · subject TEXT (nullable, email)
  raw_text TEXT · extracted_text TEXT · source_url TEXT (nullable)
  risk_level TEXT · is_scam INTEGER · scam_category TEXT · tactics TEXT (json) · language TEXT
  confidence REAL · verdict TEXT (json) · created_at TEXT (indexed)

scam_of_week
  id INTEGER pk · week TEXT · title TEXT · body TEXT · image_url TEXT · language TEXT
```
The **trends / scam-intelligence** feed = simple `GROUP BY scam_category, risk_level` aggregates over `reports`,
filtered by `created_at` window. No separate analytics infra.

---

## 10. API surface

Under `/api/v1` (+ `/health`). FastAPI auto-serves `/openapi.json`, `/docs`, `/redoc`.

| Method & path | Purpose | Consumers |
|---|---|---|
| `POST /api/v1/check` | **Core.** `multipart`: optional `text`, `image`, `audio`, `url`. Runs the agent → `Verdict` + `report_id`. | web, Flutter, test |
| `GET /api/v1/reports` · `GET /api/v1/reports/{id}` | History / single report. | web, Flutter |
| `POST /api/v1/guardians/invite` · `POST /api/v1/guardians/link` · `GET /api/v1/guardians` | Family pairing loop. | web, Flutter, bot |
| `POST /api/v1/email-accounts` · `GET /api/v1/email-accounts` | Link/list a monitored inbox to an elder (optional; `.env` covers the single-inbox demo). | web, Flutter |
| `GET /api/v1/intelligence/trends` · `/stats` | Aggregated trending scams (SQLite GROUP BY). | dashboard |
| `GET /health` | Liveness. | infra |

Telegram is **not** a webhook endpoint — the bot uses long polling (§11), so there's no `/telegram/webhook` route.

---

## 11. Telegram bot design (long polling)

- **Setup:** `@BotFather` → `/newbot` → `TELEGRAM_BOT_TOKEN`. `/setcommands`, `/setdescription`.
- **No webhook, no tunnel.** In FastAPI `lifespan`: `await app.initialize()`, `await app.start()`,
  `await app.updater.start_polling()` as a background task; stop them on shutdown. The bot pulls updates from Telegram
  itself — works on `localhost`, nothing public required.
- **Intake mapping (reactive channel):**
  - text → `message.text`
  - screenshot → `message.photo[-1]` → `get_file` → download → SenseNova/Kimi-vision
  - voice → `message.voice` (OGG/Opus) → download → ffmpeg → Whisper (also handle `audio`/`document`)
  - link → URL entities (`type=="url"` slice; `type=="text_link"` → `entity.url`; captions use `caption_entities`)
- **Guardian pairing** (a bot can't message someone who never `/start`-ed it): elder `/invite` → 6-char code; guardian
  `/start` then `/guardian <code>` → capture guardian `chat_id`, link, status `active`.
- **Family alert** (`alert_service`): fired on a forwarded **high-risk** item *and* on a **scam email** (§7) →
  `bot.send_message(guardian_chat_id, …)`.
- **Scam of the week:** PTB `JobQueue.run_daily` over subscribed `chat_id`s.
- **Replies** (`bot/replies.py`): render the `Verdict` into a calm message in `verdict.language` with a 🔴🟡🟢 prefix.

---

## 12. Web + Flutter readiness (OpenAPI codegen)

The backend is the single source of truth; both clients are **generated**.
- Set `FastAPI(generate_unique_id_function=...)` for short/stable `operationId`s (clean method names that don't churn).
- **Web (React/TS):** `npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o frontend/src/client`
- **Flutter (Dart):** `npx @openapitools/openapi-generator-cli generate -g dart-dio -i http://localhost:8000/openapi.json -o mobile/lib/api`
- `scripts/gen_clients.sh` runs both. `frontend/` and `mobile/` are stub folders with READMEs now; **no app code this phase.**
- **CORS:** explicit origins (web dev + deployed); never `["*"]` with credentials.

---

## 13. Configuration & secrets (`.env`)

`backend/.env.example` (committed; real `.env` gitignored). Loaded via `pydantic-settings`.

```dotenv
# --- App ---
ENV=dev
CORS_ORIGINS=["http://localhost:5173"]

# --- Storage (SQLite, single file) ---
DATABASE_URL=sqlite+aiosqlite:///./scamguardian.db

# --- Telegram (long polling — NO webhook/tunnel needed) ---
TELEGRAM_BOT_TOKEN=123456789:AAH...           # @BotFather

# --- LLM (pick ONE base_url) ---
LLM_BASE_URL=https://api.moonshot.ai/v1       # or https://api.tokenrouter.io/v1
LLM_API_KEY=sk-...                            # MOONSHOT key, or tr_... for TokenRouter
LLM_MODEL_BRAIN=kimi-k2.6
LLM_MODEL_TRIAGE=kimi-k2.6

# --- Autonomous email monitoring (CHANNEL B) ---
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_USER=demo.elder@gmail.com
EMAIL_IMAP_PASSWORD=<gmail-app-password>      # Gmail App Password (2FA on, IMAP enabled)
EMAIL_POLL_SECONDS=20
EMAIL_OWNER_ELDER_ID=1                         # which elder this inbox belongs to (demo single-inbox)

# --- Sponsors (leave blank to use fallbacks) ---
SENSENOVA_API_KEY=
SENSENOVA_BASE_URL=https://token.sensenova.cn/v1
VIDEO_DB_API_KEY=
BRIGHTDATA_API_TOKEN=
BRIGHTDATA_SERP_ZONE=serp_api1
BRIGHTDATA_UNLOCKER_ZONE=unblocker
DAYTONA_API_KEY=

# --- STT ---
STT_PROVIDER=whisper                           # whisper | videodb
```

---

## 14. Milestones / build order

Backend-first; riskiest-thing-first; each ends with a verifiable check.

- **M0 — Scaffold.** `pyproject.toml`, FastAPI app, `/health`, `config.py`, `db.py` (SQLite + `init_db()` create tables). ✅ `GET /health` ok; `scamguardian.db` created.
- **M1 — The brain (highest priority).** `agent/` graph for **text-only**: intake → analyze → synthesize → strict `Verdict`; `make_llm()` → Kimi. ✅ `POST /api/v1/check` (text) returns a correct multilingual Verdict. *Don't move on until reliable.*
- **M2 — Telegram round-trip (long polling).** Bot token, polling in lifespan, text handler → `check_service` → reply. ✅ A judge texts the bot, gets a verdict — no tunnel.
- **M3 — Family loop.** `guardian_links`, `/invite` + `/guardian <code>`, `alert_service` fires on high risk. ✅ High-risk forward pings the guardian.
- **M4 — 📧 Autonomous email alert (the new feature).** `email_accounts` + IMAP poller → `check_service` → `alert_service`. ✅ Send a scam email to the demo inbox; ~20s later the family's phone buzzes with the alert.
- **M5 — Screenshots.** `ocr` node: SenseNova (Kimi-vision fallback). ✅ Forwarded image → verdict.
- **M6 — Links.** `link_intel` node: Bright Data; optional Daytona; `verify` ToolNode consumes it. ✅ Suspicious URL → verdict cites domain age/impersonation.
- **M7 — Voice.** `transcribe` node: Whisper (VideoDB flag), ffmpeg OGG→mp3. ✅ Voice note → verdict.
- **M8 — Trends API.** `intelligence/trends` + `stats` SQLite aggregates. ✅ Endpoint returns trending scams.
- **M9 — Contract export & client stubs.** stable `operationId`s, export `docs/openapi.json`, prove `gen_clients.sh` makes TS + Dart clients. ✅ Both generate cleanly.
- **M10 — Polish & demo.** `/setcommands`, scam-of-week job, seed demo data, run instructions.

> Demo priority order if time is short: **M1 → M2 → M3 → M4** (text verdict + bot + family loop + autonomous email
> alert) is the headline demo. Screenshots/links/voice/trends are the "and it also does…" additions.

---

## 15. De-risking & key decisions

1. **SQLite, demo-only.** One file, created on startup, no migrations/queue/tunnel. Production path (Postgres,
   Alembic, ARQ, webhooks) is documented but **out of scope** — don't build it until needed.
2. **Telegram long polling, not webhooks.** Removes the public-HTTPS/tunnel requirement entirely and the webhook
   retry-storm concern — the agent can run inline in the handler for the demo.
3. **Autonomous email = IMAP polling.** Simplest mechanism that works with any Gmail demo account (App Password). IMAP
   IDLE / provider webhooks are noted upgrades. Alert threshold = `is_scam and risk_level=="high"` (tune as needed).
4. **Voice STT: Whisper primary.** VideoDB lacks Malay/Tamil (2 of 4 languages); Whisper covers all four and ingests
   OGG. VideoDB stays as the sponsor path behind `STT_PROVIDER=videodb`.
5. **SenseNova hosted id unconfirmed** → configurable model + **Kimi-vision OCR fallback**; SenseNova's unique role is
   the scam-of-week card image.
6. **Kimi has no free API tier** → `make_llm()` makes the provider one env change (Kimi ↔ TokenRouter ↔ OpenRouter).
7. **Hostile content** (fetched pages, email HTML) → strip to text + sanitize before any LLM; open links only inside
   Daytona/Bright Data.

---

## 16. Local dev & run

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (mac/linux: . .venv/bin/activate)
pip install -e .                    # from pyproject
copy .env.example .env              # then fill in TELEGRAM_BOT_TOKEN, LLM_API_KEY, EMAIL_* (PowerShell: copy)
uvicorn app.main:app --reload       # http://localhost:8000/docs
#   on startup the lifespan: creates the SQLite tables, starts the Telegram bot (long polling),
#   and starts the email-monitor poller. No tunnel, no migrations.
```
Prereqs: Python 3.12+, **ffmpeg** on PATH (voice), a Telegram bot token, and (for Channel B) a Gmail App Password with
IMAP enabled. No database server, no public URL.

---

## 17. Success criteria

- [ ] A judge texts the **Telegram bot** and gets a correct, simple verdict live (no tunnel needed).
- [ ] **Autonomous:** a scam email sent to the demo inbox triggers a **family alert** in Telegram within ~20s, naming whose inbox and the trick — *without anyone forwarding it.*
- [ ] The **family loop** also fires on a forwarded high-risk item.
- [ ] At least three input types work (text, screenshot, voice) and the verdict names the **tactic** in 2+ languages.
- [ ] `GET /api/v1/intelligence/trends` returns aggregated trending scams from SQLite.
- [ ] `/openapi.json` exported; TS + Dart clients generate cleanly (web + Flutter readiness proven).
- [ ] ≥3 sponsors integrated meaningfully (Kimi + SenseNova + Bright Data minimum).

---

## 18. Open questions / assumptions

**Assumptions (say the word to change any):**
- Backend = **Python**; storage = **SQLite file**; Telegram = **long polling**; email = **IMAP polling** of one Gmail demo inbox via App Password.
- Email alert fires on `is_scam and risk_level=="high"`; recipients = the elder's active guardians.
- This phase delivers **no frontend code** — contract + stub folders + codegen scripts only.
- README stays the pitch; **PLAN.md is authoritative** where they differ.

**Need confirmation:**
- Which email provider for the demo inbox — **Gmail** (App Password) ok, or another?
- Should the **elder also** get a Telegram message on a scam email, or **family only**?
- Sponsor scope: keep all six (tiered, with fallbacks) or trim to the core three?
