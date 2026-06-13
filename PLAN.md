# 🛡️ Scam Guardian — Build Plan (Demo-first, SQLite, Telegram, multi-phase LangGraph agent)

> This is the **authoritative technical plan**. [README.md](README.md) is the product/market pitch and stays as-is.
> Where the README says **WhatsApp**, we build on **Telegram** instead (rationale in §1). The business model, market,
> and demo narrative in the README are channel-agnostic and still hold.

**Scope:** build a **working demo backend** that runs **fully locally as one process** — no production hardening. The
scam-detection "brain" is a **multi-phase agent built on LangChain + LangGraph**. Storage is **SQLite** (a single
local file). Two input channels feed the same brain:
1. **Reactive** — a *verified* user forwards a suspicious text / screenshot / voice note / link to the Telegram bot.
2. **Autonomous** — the system *watches a real Gmail inbox* and, when a scam email arrives, **automatically alerts the
   linked family members** through the bot. No forwarding needed.

Everything is designed so a **web app (React/TS)** and a **Flutter (Dart) mobile app** can be added later with zero
backend rework — but **no frontend code is built this phase.**

---

## 0. Locked demo requirements (confirmed with the user)

These are firm. Every section below is built to satisfy them:

1. **Real Telegram bot, runnable now.** You provide a real `@BotFather` token; the bot connects for real (long
   polling) — no mock, no stub. (§11, §16)
2. **Verified members only.** The bot ignores strangers. A person becomes a member by entering a shared access code
   once (`/verify <code>`); only the resulting allowlist can use it. Everyone else gets a polite "not authorized."
   An admin can `/approve` / `/revoke`. (§9 `users.verified`, §11 verification gate)
3. **One local process runs everything.** A single command (`python -m app`) starts the API **and** the Telegram bot
   **and** the autonomous email monitor in one process. While it runs, the agent is fully autonomous; `Ctrl+C` stops
   everything. (§16)
4. **Linked to a real Gmail you provide.** Access is via a **Gmail App Password** (exact steps in §7.4). You can then
   demo by sending a phishing email to that account and watching the family alert fire.
5. **Detect impostor / spoofed senders — every shape of phishing.** Beyond message wording, the agent runs **email
   forensics**: display-name vs real-address mismatch, lookalike/cousin domains, homoglyph/punycode (IDN), freemail
   pretending to be a company, Reply-To/Return-Path mismatch, link-text vs href mismatch, and SPF/DKIM/DMARC failures.
   (§7.3)
6. **Bilingual output — English + 中文 together.** Every Telegram reply and family alert shows the reason and the next
   step in **both English and Chinese**, side by side. (§6, §11)
7. **Verdict shows WHY + confidence %.** The reply states the risk light, a **confidence percentage**, the named
   tactic(s), and the plain-language reason. (§6, §11)

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
16. [Local dev & run (one process)](#16-local-dev--run-one-process)
17. [Success criteria](#17-success-criteria)
18. [Open questions / assumptions](#18-open-questions--assumptions)

---

## 1. What changed vs. the README

| README says | This plan does | Why |
|---|---|---|
| WhatsApp via Twilio | **Telegram bot** (long polling) | Free, instant `@BotFather` setup; native text/photo/voice/link; can proactively message family; **long polling needs no public URL/tunnel** — ideal for a local demo. |
| "Kimi agent swarm" | **LangGraph state machine** with parallel `analyze ∥ verify` | The swarm as an explicit, debuggable graph. "Multi-phase using LangChain" = LangGraph. |
| Only reactive (user forwards) | **+ Autonomous email monitoring** | Watch a real inbox; on a scam email, auto-alert the family — even if the elder never forwards it. (§7) |
| Open to anyone | **Verified members only** | The bot serves only an access-code-verified allowlist. (§11) |
| One language at a time | **Bilingual EN + 中文 always** | Replies/alerts show both, with a confidence %. (§6, §11) |
| Production data product | **SQLite, demo-only** | One local file, zero infra. Trends = simple aggregate queries over the `reports` table. |
| One-day full stack | **Backend-first**, contract-driven | Web + Flutter consume the same OpenAPI contract later; no frontend code now. |

**Deliberately NOT used** (per "don't use it if there's no need"): Postgres/Supabase, Alembic migrations, Redis/ARQ
queue, cloudflared/ngrok tunnel, Telegram webhooks, Gmail OAuth. All are noted as the production upgrade path but
excluded from the demo build.

---

## 2. Architecture (updated)

```
 ┌─ CHANNEL A: Telegram (reactive, VERIFIED members only) ─┐   ┌─ CHANNEL B: real Gmail inbox (autonomous) ─┐
 │  member forwards text/photo/voice/link                  │   │  a new email arrives in the inbox          │
 └──────────────┬──────────────────────────────────────────┘   └──────────────────┬─────────────────────────┘
                │ bot (LONG POLLING — no tunnel)                                    │ IMAP poller (~every 20s)
                ▼                                                                   ▼
   ┌──────────────────────── LangGraph multi-phase agent (one brain) ─────────────────────────────┐
   │  1 intake/normalize  → modality + language                                                    │
   │  2 route (cond. edge)                                                                          │
   │  3 extract (parallel): image→SenseNova U1 (Kimi-vision fallback) · voice→Whisper(/VideoDB)     │
   │                        · link→Bright Data(+Daytona) · EMAIL→sender forensics · text→passthrough│
   │  4 analyze ∥ verify  (the swarm): Kimi k2.6 tactic detection  +  tool/forensics verification   │
   │  5 synthesize        → strict Verdict JSON: bilingual EN+中文, confidence %, named tactics, why │
   │  6 decide            → reply / save / alert family                                             │
   └────────────────────────────────────────────────────────────────────────────────────────────-─┘
                │                          │                              │
                ▼                          ▼                              ▼
        reply to the member        save to SQLite               if scam(high) → alert FAMILY via bot
        (bilingual + conf %)       (reports → trends)            • forwarded high-risk item, OR
                                                                 • scam EMAIL: "📧 Mum's inbox got a scam
                                                                   email from <sender> …" (bilingual)

   ALL THREE — API, Telegram bot, email poller — run inside ONE local process (§16).
   (Web + Flutter later call the SAME brain via POST /api/v1/check. LLM via make_llm() → Kimi by default.)
```

---

## 3. Tech stack & why

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.12+** | LangGraph is Python-first; pairs with FastAPI. |
| Web framework | **FastAPI** + Uvicorn | Async; auto **OpenAPI 3.1** = the shared contract for web + Flutter. |
| Schemas | **Pydantic v2** | Request/response + the `Verdict` contract. |
| Agent engine | **LangGraph 1.2.x** (`langgraph>=1.2,<2`) + `langchain>=1.3,<2` + `langchain-openai>=1.2,<2` | StateGraph, conditional edges, `Send` fan-out, `ToolNode`, `with_structured_output`. |
| LLM "brain" | **Kimi k2.6** (Moonshot), OpenAI-compatible | `base_url=https://api.moonshot.ai/v1`, model `kimi-k2.6` (**dot, not dash**), 256K ctx, vision + json output. Strong on Chinese + English. |
| LLM gateway | **TokenRouter** (optional, OpenAI-compatible) | Env-flip to `https://api.tokenrouter.io/v1`; off by default. |
| **Storage** | **SQLite** via **SQLModel** (+ `aiosqlite`) | Single file `scamguardian.db`. Tables created on startup — **no Alembic.** |
| Telegram | **python-telegram-bot v22** (`[job-queue]`) | **Long polling** inside the process — no webhook, no public URL. |
| Email intake | **IMAP** via `imaplib` (stdlib) + stdlib `email` | Poll a real Gmail inbox via **App Password**. IMAP IDLE = optional "instant" upgrade. |
| Email forensics | **stdlib `email` + `tldextract` + `idna`** | Header parsing, domain extraction, homoglyph/punycode + lookalike scoring (§7.3). |
| STT | **faster-whisper** (primary) / **VideoDB** (sponsor path) | VideoDB lacks Malay & Tamil — see §15. |
| Screenshot OCR | **SenseNova U1** (sponsor) / **Kimi-vision** (fallback) | SenseNova also generates the scam-of-week card. |
| Link intel | **Bright Data** + **Daytona** (optional) | Domain age + brand-lookalike + this-week cross-ref. |
| Process model | **one process** (uvicorn + lifespan tasks) | API + bot polling + email poller in a single `python -m app`. |

---

## 4. Repository layout

```
ai-agent-hackathon/
├── README.md · PLAN.md · PLAN-SIMPLE.md · .gitignore
├── backend/                  # ← all work this phase
│   ├── pyproject.toml · .env.example · scamguardian.db (gitignored)
│   ├── app/
│   │   ├── __main__.py       # `python -m app` → starts uvicorn (one process, everything)
│   │   ├── main.py           # FastAPI app + lifespan (create tables, start bot polling, start email poller), CORS
│   │   ├── core/
│   │   │   ├── config.py     # pydantic-settings BaseSettings
│   │   │   └── db.py         # async SQLite engine + get_session() + init_db()
│   │   ├── models/           # SQLModel table=True models
│   │   ├── schemas/          # Pydantic v2 (incl. Verdict, SenderAnalysis) = the CONTRACT
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routers/  check.py · reports.py · guardians.py · email_accounts.py · intelligence.py
│   │   ├── bot/
│   │   │   ├── telegram_bot.py   # build_application(), verification gate, handlers, /commands
│   │   │   └── replies.py        # format Verdict → BILINGUAL message with confidence %
│   │   ├── ingest/
│   │   │   └── email_monitor.py  # IMAP poll loop → check_service → alert (CHANNEL B)
│   │   ├── agent/
│   │   │   ├── state.py · graph.py · prompts.py · llm.py · verdict.py
│   │   │   └── nodes/  intake · extract · analyze · verify · synthesize · decide
│   │   ├── integrations/  sensenova.py · whisper_stt.py · videodb_stt.py · brightdata.py · daytona.py
│   │   │                  · email_forensics.py   # impostor/spoofed-sender detection (§7.3)
│   │   └── services/  check_service.py · guardian_service.py · alert_service.py · intelligence_service.py
│   │                  · member_service.py   # verified-allowlist logic (§11)
│   ├── scripts/  (gen_clients.sh · seed.py · set_bot_commands.py)
│   └── tests/
├── frontend/  README.md      # placeholder: codegen TS client into src/client from /openapi.json
├── mobile/    README.md      # placeholder: codegen dart-dio client into lib/api
└── docs/openapi.json         # exported contract (generated)
```

**Key principle:** every entry point (Telegram forward, email poller, REST `/check`) calls the **same**
`check_service` and `alert_service`. One brain, one alert path.

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
    source: dict                     # {channel:"telegram"|"email"|"web", who:..., sender_raw:...}
    raw_text: str                    # text / email body / caption
    image_bytes: Optional[bytes]
    audio_path: Optional[str]
    urls: list[str]
    email_headers: Optional[dict]    # From, Reply-To, Return-Path, Authentication-Results (email only)
    modality: Modality
    language_hint: Optional[str]
    extracted_text: Annotated[list[str], lambda a, b: a + b]   # reducers → parallel writes merge
    link_intel: Annotated[list[dict], lambda a, b: a + b]
    sender_analysis: Optional[dict]  # filled by email_forensics for the email channel
    messages: Annotated[list, add_messages]
    analysis: Optional[dict]
    verification: Optional[dict]
    verdict: Optional[Verdict]
```
> **Gotcha (verified):** parallel branches writing the same key raise `InvalidUpdateError` without a reducer — hence
> the `a + b` reducers and `add_messages`.

### The six phases
| Phase | Node(s) | What it does |
|---|---|---|
| 1 Intake | `intake` | Normalize input; set `modality`; detect language. Email also parses headers + runs `email_forensics` → `sender_analysis`. |
| 2 Route | `add_conditional_edges("intake", route_by_modality, {...})` | Fan out by modality (`Send` for multi-attachment). |
| 3 Extract | `ocr`, `transcribe`, `link_intel`, text/email→straight | Each writes `extracted_text` / `link_intel`; parallel. |
| 4 Analyze ∥ Verify | `analyze`, `verify` | The swarm: Kimi tactic detection + `ToolNode`/forensics checks. Both join at synthesize. |
| 5 Synthesize | `synthesize` | `llm.with_structured_output(Verdict, method="json_schema")` → strict JSON, **bilingual EN+中文**, with confidence. |
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

### System prompt (`app/agent/prompts.py`)
Start from the README's paste-ready Kimi prompt, with three changes locked in:
1. **Bilingual output** — fill **both** `explanation_en` & `explanation_zh`, and `action_en` & `action_zh`, every
   time (not "the detected language"). Chinese = Simplified.
2. **Use `sender_analysis`** — when present, the model must reference concrete sender facts in the explanation
   (e.g. *"the sender pretends to be DBS but the real address is alerts@dbs-verify.ru"*).
3. **Confidence** — return a `confidence` 0–1 that the reply renders as a %.
Disable k2.6 `thinking` mode on the fast path to cut latency.

---

## 6. The shared contract: `Verdict` schema

```python
# app/agent/verdict.py
from typing import Literal, Optional
from pydantic import BaseModel, Field

class SenderAnalysis(BaseModel):
    from_display_name: Optional[str] = None      # "DBS Bank Security"
    from_address: Optional[str] = None           # real, e.g. alerts@dbs-verify.ru
    claimed_brand: Optional[str] = None           # brand the sender pretends to be
    display_name_mismatch: bool = False           # name claims brand X, address isn't X's domain
    lookalike_domain: bool = False                # cousin / homoglyph / punycode of a real brand
    freemail_as_company: bool = False             # gmail/outlook address claiming to be a company
    replyto_mismatch: bool = False                # Reply-To / Return-Path differ from From
    auth_results: Optional[str] = None            # e.g. "spf=fail dkim=none dmarc=fail"
    reasons: list[str] = Field(default_factory=list)

class Verdict(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    is_scam: bool
    confidence: float = Field(ge=0, le=1, description="0..1; shown to the user as a %")
    tactics: list[str] = Field(default_factory=list, description="named tactics; [] if none")
    scam_category: Optional[str] = Field(default=None,
        description="bank_impersonation | govt_official | phishing | lottery | romance | job | other")
    # BILINGUAL — always fill BOTH languages (requirement 6)
    explanation_en: str = Field(description="1–2 simple sentences a 70-year-old understands (English)")
    explanation_zh: str = Field(description="同上，简体中文")
    action_en: str = Field(description="the single clearest next step (English)")
    action_zh: str = Field(description="同上，简体中文")
    sender_analysis: Optional[SenderAnalysis] = None      # email channel; null elsewhere
    input_language: str = Field(description="detected language of the original input: en | zh | ms | ta | other")
    alert_family: bool = Field(description="true when risk_level == 'high'")
```
This one model flows through the agent, the API, the Telegram reply, the email alert, and (via OpenAPI codegen) into
the TS and Dart clients.

---

## 7. Autonomous email monitoring → family alert

**The new feature.** Instead of waiting for the elder to forward something, Scam Guardian *watches a real inbox* and
alerts the family the moment a scam email arrives.

### 7.1 Flow
```
new email in inbox  →  IMAP poller fetches it  →  parse sender/subject/body/urls + headers
   →  email_forensics(headers) → sender_analysis (§7.3)
   →  check_service runs the SAME agent  →  bilingual Verdict
   →  if is_scam and risk_level == "high":
        inbox → owner (elder) → their active guardians (guardian_links)
        → bot.send_message(each guardian): bilingual alert naming whose inbox + sender + why + confidence %
   →  save a report row (channel='email') for the trends data
```

### 7.2 How "an email reached the inbox" is detected (demo-simple)
- A background `asyncio` task in the process lifespan **polls IMAP every ~20s** for `UNSEEN` messages (`imaplib` in a
  thread). Parse with stdlib `email`, strip HTML → plain text, extract URLs + headers, run the agent, alert if scam,
  mark `\Seen`. **Optional upgrade:** IMAP **IDLE** for near-instant push.

### 7.3 Impostor / spoofed-sender detection (every shape of phishing) — requirement 5
`app/integrations/email_forensics.py` computes **deterministic** signals from the raw headers *before* the LLM sees
the content, and passes them in as `sender_analysis`. Strong signals push the verdict to high risk even if the wording
looks innocent.

| Check | Catches (example) | How |
|---|---|---|
| Display-name vs real address | `"DBS Bank" <noreply@dbs-verify.ru>` | parse `From` → name + addr; addr domain ≠ the brand the name claims |
| Lookalike / cousin domain | `dbs-secure.com`, `dbs.com.verify.ru` | string distance + known-brand list; flag added words / hyphens / wrong TLD |
| Homoglyph / punycode (IDN) | `paypa1.com`, `аpple.com` (Cyrillic), `xn--…` | mixed-script / `xn--` prefix detection via `idna`/`tldextract` |
| Freemail-as-company | `"IRAS Tax" <iras.refund@gmail.com>` | company claim from gmail/outlook/yahoo/qq etc. |
| Reply-To / Return-Path mismatch | From bank, Reply-To random | compare headers |
| Auth failure (SPF/DKIM/DMARC) | forged sender domain | read `Authentication-Results` → fail/none |
| Link text vs href mismatch | shows `dbs.com.sg`, links to `evil.ru` | compare anchor text to real href |
| Brand-domain truth check | is the claimed brand's *real* domain? | Bright Data SERP resolves the brand's canonical domain to compare |

The explanation then states concrete facts (*"pretends to be DBS, real address is alerts@dbs-verify.ru, which is not
DBS; the bank link actually points to evil.ru"*) — not vague hand-waving.

### 7.4 How to give the agent access to your Gmail (App Password — do once) — requirement 4
You provide a real Gmail account; connect it with an **App Password** (no OAuth needed):
1. On that Google account, turn on **2-Step Verification** (myaccount.google.com → Security). Required for App Passwords.
2. Open **myaccount.google.com/apppasswords**, create one named "ScamGuardian" → Google shows a **16-character** password. Copy it.
3. Gmail **Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP → Save**.
4. Put these in `backend/.env` (gitignored — the secret never reaches GitHub):
   ```
   EMAIL_IMAP_HOST=imap.gmail.com
   EMAIL_IMAP_USER=the.demo.account@gmail.com
   EMAIL_IMAP_PASSWORD=xxxxxxxxxxxxxxxx     # the 16-char App Password (spaces optional)
   ```
**What you give me:** just the Gmail address + the App Password — paste them into `.env` yourself (preferred), or send
them and I'll place them. **Use a throwaway/demo Gmail, not a personal one.** To demo: send a phishing-style email to
that address → ~20s later the family account gets the bilingual Telegram alert. *(Production path: Gmail API OAuth.)*

### 7.5 Who gets alerted
Reuses **`guardian_links`**: the monitored inbox maps to an **elder** (via `email_accounts`, or `EMAIL_OWNER_ELDER_ID`
in `.env` for the single-inbox demo); that elder's **active guardians** receive the alert. Optionally also notify the
elder.

### 7.6 Safety
Email HTML is attacker-controlled → **strip to plain text and sanitize before the LLM sees it** (prompt-injection
risk). Never auto-open links except inside Daytona/Bright Data.

---

## 8. Sponsor integrations (verified, with fallbacks)

> Each lives behind a thin client in `app/integrations/`, so any can be stubbed. Tiers: 🟢 load-bearing, 🟡 showcase
> (has a fallback). Confidence is from the June-2026 research sweep.

### Kimi k2.6 — the brain · 🟢 · confidence: high
- **Auth:** key from `platform.kimi.ai/console/api-keys` (old `platform.moonshot.ai` redirects there). Env `LLM_API_KEY`. **No free tier** (min $1 recharge); hackathon alt: Kimi via **OpenRouter**/TokenRouter credits.
- **Endpoint:** `https://api.moonshot.ai/v1` (global) / `.cn` (China, separate key). OpenAI-compatible. Model `kimi-k2.6` (dot). Vision via `image_url` data-URI. Strong Chinese+English → good fit for bilingual output.
- **Use:** phase-4 analyze + phase-5 synthesize (json output); screenshot OCR fallback.

### Bright Data — link/domain verification + brand-domain truth · 🟢 · confidence: high
- **Auth:** Bearer `BRIGHTDATA_API_TOKEN` + a **zone**. ~5000 free req/month.
- **Endpoint:** `POST https://api.brightdata.com/request` with `{zone, url, format}` (Unlocker `raw` / SERP `json`).
- **Use:** WHOIS-page fetch → domain age; SERP brand → canonical domain (feeds the §7.3 brand-domain check); SERP `"<url>" scam` → this-week cross-ref. **Treat fetched HTML as hostile.**

### SenseNova U1 — screenshot OCR + scam-of-week card · 🟡 (fallback: Kimi-vision) · confidence: medium
- Hosted OpenAI-compatible `https://token.sensenova.cn/v1` (free beta) **or** self-host Apache-2.0 weights via vLLM-Omni.
- **⚠** exact hosted "U1" model id unconfirmed → keep `SENSENOVA_BASE_URL` + model configurable; **Kimi-vision** is the OCR fallback. Unique value = the scam-of-week **card image**.

### VideoDB — voice transcription · 🟡 (primary: Whisper) · confidence: medium
- `pip install videodb`; `connect → upload → audio.generate_transcript → get_transcript_text`. **⚠ no Malay/Tamil** → **Whisper is primary** (§15). VideoDB stays for EN/ZH + future video search.

### Whisper — primary STT · confidence: high
- `faster-whisper` (local). Handles OGG/Opus and **all four** languages in one model.

### Daytona — safe link sandbox (runs on user-forwarded links AND email links) · 🟡 · confidence: high
- `pip install daytona`; `create() → sandbox.process.exec("curl -sSIL …") → delete()` in `finally`. ~$200 starter + hackathon credits.
- **When it fires:** whenever a link reaches the `link_intel` node — either a verified member **forwards/pastes a link to the bot**, or a **scam email contains one** — the agent opens it in a fresh, disposable Daytona sandbox to resolve redirects/final URL/content-type, then deletes the sandbox. Keeps the suspicious page off the elder's device and our host. Bright Data adds the domain/brand signals; Daytona is the safe "open it and look" step.

### TokenRouter — LLM gateway · 🟡 (off by default) · confidence: medium
- `https://api.tokenrouter.io/v1` (OpenAI-compatible), keys `tr_…`, modes `auto:cost|fast|balance|quality`. **BYO provider keys**. Not OpenRouter. Flip on via `make_llm()` env.

---

## 9. Data model (SQLite)

SQLModel tables, created on startup (`SQLModel.metadata.create_all`). No migrations.

```
users
  id INTEGER pk · telegram_chat_id INTEGER (unique, nullable) · telegram_user_id INTEGER (unique, nullable)
  name TEXT · language TEXT default 'en' · role TEXT ('elder'|'guardian'|'both')
  verified INTEGER default 0 · is_admin INTEGER default 0 · created_at TEXT
  -- VERIFIED GATE (req 2): only verified=1 users may use the bot; is_admin can /approve, /revoke

guardian_links
  id INTEGER pk · elder_id fk · guardian_id fk (nullable until claimed)
  pairing_code TEXT (unique) · status TEXT ('pending'|'active'|'revoked') · created_at TEXT

email_accounts                          -- maps a monitored inbox → an elder (CHANNEL B)
  id INTEGER pk · elder_id fk · email_address TEXT (unique) · imap_host TEXT · active INTEGER
  -- demo: a single inbox can instead be set via EMAIL_OWNER_ELDER_ID in .env

reports                                  -- one per checked item; feeds the trends product
  id INTEGER pk · user_id fk (nullable) · channel TEXT ('telegram'|'email'|'web')
  modality TEXT · sender TEXT (nullable) · subject TEXT (nullable)
  raw_text TEXT · extracted_text TEXT · source_url TEXT (nullable)
  risk_level TEXT · is_scam INTEGER · confidence REAL · scam_category TEXT · tactics TEXT(json)
  sender_analysis TEXT(json, nullable) · input_language TEXT · verdict TEXT(json) · created_at TEXT (indexed)

scam_of_week
  id INTEGER pk · week TEXT · title TEXT · body TEXT · image_url TEXT · language TEXT
```
**Trends feed** = simple `GROUP BY scam_category, risk_level` over `reports` by `created_at` window. No analytics infra.

---

## 10. API surface

Under `/api/v1` (+ `/health`). FastAPI auto-serves `/openapi.json`, `/docs`, `/redoc`.

| Method & path | Purpose |
|---|---|
| `POST /api/v1/check` | **Core.** `multipart`: optional `text`/`image`/`audio`/`url`. Runs the agent → `Verdict` + `report_id`. |
| `GET /api/v1/reports` · `GET /api/v1/reports/{id}` | History / single report. |
| `POST /api/v1/guardians/invite` · `/link` · `GET /api/v1/guardians` | Family pairing loop. |
| `POST /api/v1/email-accounts` · `GET …` | Link/list a monitored inbox (optional; `.env` covers the demo). |
| `GET /api/v1/intelligence/trends` · `/stats` | Aggregated trending scams (SQLite GROUP BY). |
| `GET /health` | Liveness. |

Telegram is **not** a webhook endpoint — the bot uses long polling (§11).

---

## 11. Telegram bot design (long polling)

- **Setup:** `@BotFather` → `/newbot` → real `TELEGRAM_BOT_TOKEN` (you provide). `scripts/set_bot_commands.py` sets `/setcommands`, `/setdescription`.
- **No webhook, no tunnel.** In the process lifespan: `await app.initialize()`, `await app.start()`, `await app.updater.start_polling()` as a task; stop on shutdown. Works on `localhost`.
- **Verified-members gate (requirement 2).** A PTB `TypeHandler` runs **before** all other handlers and checks the sender's `telegram_user_id` against `users.verified`. First contact → bot replies *"Welcome — please enter your access code: `/verify <code>`"*. Correct `ACCESS_CODE` (from `.env`) → mark `verified=1`, onboard. Unverified users are politely refused. `ADMIN_TELEGRAM_ID` can `/approve <id>` / `/revoke <id>`.
- **Two modes, both always on.** (1) **Interactive** — a verified member can **send or forward anything** (a link they're unsure about, typed text, a screenshot, a voice note) and the bot **analyzes it and replies** with the bilingual verdict. They can literally just paste a suspicious link and get an answer. (2) **Autonomous** — independently and at the same time, the email monitor scans the inbox and **pushes warnings on its own**, with no message from anyone. The same process runs both.
- **Intake mapping (interactive channel):** the handler accepts **any** message from a verified member —
  - text → `message.text`
  - screenshot → `message.photo[-1]` → `get_file` → SenseNova/Kimi-vision
  - voice → `message.voice` (OGG) → ffmpeg → Whisper
  - **link** → URL entities (`url` slice / `text_link` → `entity.url`; captions use `caption_entities`) → routed to the `link_intel` node: **Bright Data** domain/brand/this-week checks **+ the link is opened safely inside a fresh Daytona sandbox** (`curl -sSIL` resolves the redirect chain, final URL, and content-type without touching the user's device) → bilingual verdict reply.
- **Guardian pairing** (a bot can't message someone who never `/start`-ed it): elder `/invite` → 6-char code; guardian `/start` then `/guardian <code>` → capture guardian `chat_id`, link, status `active`.
- **Family alert** (`alert_service`): fired on a forwarded **high-risk** item *and* a **scam email** (§7) → `bot.send_message(guardian_chat_id, …)`.
- **Bilingual replies & alerts with confidence % (requirements 6 & 7).** `bot/replies.py` renders the `Verdict` as:
  ```
  🔴 SCAM · 92% sure   |   诈骗 · 92% 确定
  🧠 Tactics: bank impersonation · urgency · sender mismatch

  EN — They pretend to be DBS and rush you to click. The real sender alerts@dbs-verify.ru is NOT DBS.
  中文 — 对方假冒星展银行（DBS）并催促你点击。真实发件人 alerts@dbs-verify.ru 并不属于 DBS。

  ✅ EN — Do not click or reply. Call DBS using the number on the back of your bank card.
  ✅ 中文 — 不要点击或回复。请拨打银行卡背面的官方电话联系星展银行。
  ```
  Lights: 🔴 high · 🟡 medium · 🟢 low. The email family-alert uses the same bilingual block, prefixed with whose inbox + the sender address.
- **Scam of the week:** PTB `JobQueue.run_daily` over subscribed verified members.

---

## 12. Web + Flutter readiness (OpenAPI codegen)

The backend is the single source of truth; both clients are **generated**.
- Set `FastAPI(generate_unique_id_function=...)` for short/stable `operationId`s.
- **Web (React/TS):** `npx @hey-api/openapi-ts -i http://localhost:8000/openapi.json -o frontend/src/client`
- **Flutter (Dart):** `npx @openapitools/openapi-generator-cli generate -g dart-dio -i http://localhost:8000/openapi.json -o mobile/lib/api`
- `scripts/gen_clients.sh` runs both. `frontend/`+`mobile/` are stub folders with READMEs now; **no app code this phase.**
- **CORS:** explicit origins; never `["*"]` with credentials.

---

## 13. Configuration & secrets (`.env`)

`backend/.env.example` (committed; real `.env` gitignored). Loaded via `pydantic-settings`.

```dotenv
# --- App ---
ENV=dev
CORS_ORIGINS=["http://localhost:5173"]
HOST=127.0.0.1
PORT=8000

# --- Storage (SQLite, single file) ---
DATABASE_URL=sqlite+aiosqlite:///./scamguardian.db

# --- Telegram (REAL bot, long polling — NO webhook/tunnel) ---
TELEGRAM_BOT_TOKEN=123456789:AAH...            # from @BotFather (you provide)

# --- Access control (verified members only — req 2) ---
ACCESS_CODE=family-2026                        # users send /verify <code> once to be allowed in
ADMIN_TELEGRAM_ID=                             # your Telegram numeric user id (can approve/revoke)

# --- LLM (pick ONE base_url) ---
LLM_BASE_URL=https://api.moonshot.ai/v1        # or https://api.tokenrouter.io/v1
LLM_API_KEY=sk-...                             # Moonshot key, or tr_... for TokenRouter
LLM_MODEL_BRAIN=kimi-k2.6
LLM_MODEL_TRIAGE=kimi-k2.6

# --- Autonomous email monitoring (real Gmail via App Password — req 4, see §7.4) ---
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_USER=the.demo.account@gmail.com
EMAIL_IMAP_PASSWORD=xxxxxxxxxxxxxxxx           # 16-char Gmail App Password
EMAIL_POLL_SECONDS=20
EMAIL_OWNER_ELDER_ID=1                          # which elder this inbox belongs to (single-inbox demo)
ALERT_THRESHOLD=high                            # alert family when is_scam and risk_level >= this

# --- Sponsors (leave blank to use fallbacks) ---
SENSENOVA_API_KEY=
SENSENOVA_BASE_URL=https://token.sensenova.cn/v1
VIDEO_DB_API_KEY=
BRIGHTDATA_API_TOKEN=
BRIGHTDATA_SERP_ZONE=serp_api1
BRIGHTDATA_UNLOCKER_ZONE=unblocker
DAYTONA_API_KEY=

# --- STT ---
STT_PROVIDER=whisper                            # whisper | videodb
```
> Output is **always bilingual EN+中文** — no setting needed.

---

## 14. Milestones / build order

Backend-first; riskiest-thing-first; each ends with a verifiable check.

- **M0 — Scaffold + one-process runner.** `pyproject.toml`, FastAPI app, `__main__.py` (`python -m app`), `/health`, `config.py`, `db.py` (SQLite + `init_db()`). ✅ One command boots the process; `GET /health` ok; `scamguardian.db` created.
- **M1 — The brain (highest priority).** Text-only graph: intake → analyze → synthesize → strict `Verdict`, **bilingual EN+中文 with confidence %**. ✅ `POST /api/v1/check` (text) returns a correct bilingual verdict. *Don't move on until reliable.*
- **M2 — Real Telegram bot + verified gate.** Real token, long polling in lifespan, `/verify <code>` gate, text handler → `check_service` → bilingual reply. ✅ Only verified members get a verdict; strangers are refused.
- **M3 — Family loop.** `guardian_links`, `/invite` + `/guardian <code>`, `alert_service` fires on high risk. ✅ High-risk forward pings the guardian (bilingual).
- **M4 — 📧 Autonomous email + impostor detection (the headline).** IMAP poller on the real Gmail; `email_forensics` (display-name/lookalike/punycode/SPF-DKIM/etc.); alert family. ✅ Send a phishing email to the inbox → ~20s later the family phone buzzes with a bilingual alert naming the sender + why + confidence %.
- **M5 — Screenshots.** `ocr`: SenseNova (Kimi-vision fallback). ✅ Forwarded image → verdict.
- **M6 — Links (interactive + safe-open).** `link_intel`: Bright Data **+ Daytona safe-open**; `verify` ToolNode. ✅ A member pastes/forwards a link to the bot → it's opened in a Daytona sandbox and the verdict cites domain age/impersonation/redirects.
- **M7 — Voice.** `transcribe`: Whisper, ffmpeg OGG→mp3. ✅ Voice note → verdict.
- **M8 — Trends API.** `intelligence/trends` + `stats`. ✅ Endpoint returns trending scams.
- **M9 — Contract export & client stubs.** stable `operationId`s, export `docs/openapi.json`, prove `gen_clients.sh`. ✅ TS + Dart clients generate cleanly.
- **M10 — Polish & demo.** bot commands, scam-of-week job, seed data, run instructions.

> Headline demo path: **M0 → M1 → M2 → M3 → M4** (one process · verified bot · bilingual verdict · family loop ·
> autonomous email scam alert with impostor detection). The rest is "and it also does…".

---

## 15. De-risking & key decisions

1. **SQLite, demo-only, one process.** One file + one `python -m app`; no migrations/queue/tunnel. Production path (Postgres, Alembic, ARQ, webhooks, Gmail OAuth) documented but **out of scope**.
2. **Telegram long polling, not webhooks.** No public URL; runs on the laptop; no retry-storm, so the agent can run inline.
3. **Verified-members gate** via access code + admin approve/revoke — keeps the demo bot private.
4. **Impostor detection is deterministic first.** Header forensics produce hard signals (auth fail, display mismatch, lookalike) independent of the LLM; the LLM explains them in plain bilingual language. This is robust even if wording is clean.
5. **Gmail via App Password**, not OAuth — one-time setup (§7.4), works with plain IMAP. Use a throwaway account.
6. **Bilingual is enforced in the schema** (separate `_en`/`_zh` fields), so the model can't "forget" a language.
7. **Voice STT: Whisper primary** (VideoDB lacks Malay/Tamil). **SenseNova hosted id unconfirmed** → Kimi-vision OCR fallback. **Kimi has no free tier** → `make_llm()` is one env flip.
8. **Hostile content** (email HTML, fetched pages) → strip + sanitize before any LLM; open links only in Daytona/Bright Data.

---

## 16. Local dev & run (one process)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # mac/linux: . .venv/bin/activate
pip install -e .                    # from pyproject
copy .env.example .env              # fill: TELEGRAM_BOT_TOKEN, ACCESS_CODE, LLM_API_KEY, EMAIL_* (see §7.4)

python -m app                       # ← ONE process = API + Telegram bot + email monitor + agent
#   http://localhost:8000/docs   ·   Ctrl+C stops everything
```
On startup the lifespan: creates SQLite tables → starts the Telegram bot (long polling) → starts the email-monitor
poller. **As long as this process runs, the agent is fully autonomous.** No tunnel, no migrations, no DB server.

**To demo the autonomous path:** connect the real Gmail (§7.4), `/verify` yourself + a "family" account in the bot,
link them as guardian, then send a phishing email to the monitored inbox → the family account gets the bilingual
alert within ~20s.

Prereqs: Python 3.12+, **ffmpeg** on PATH (voice), the real Telegram bot token, and a Gmail App Password (§7.4).

---

## 17. Success criteria

- [ ] **One `python -m app`** boots API + bot + email monitor; the bot is a **real** Telegram bot.
- [ ] **Verified-only:** a stranger is refused; `/verify <code>` admits a member.
- [ ] A verified member texts the bot and gets a correct verdict — **bilingual EN+中文, with a confidence %, naming the tactic and why.**
- [ ] **Autonomous + impostor detection:** a phishing email (spoofed display name / lookalike domain) sent to the real Gmail triggers a **bilingual family alert** within ~20s — *without anyone forwarding it* — naming the real sender and why.
- [ ] The family loop also fires on a forwarded high-risk item.
- [ ] `GET /api/v1/intelligence/trends` returns aggregated trending scams from SQLite.
- [ ] `/openapi.json` exported; TS + Dart clients generate cleanly (web + Flutter readiness proven).
- [ ] ≥3 sponsors integrated meaningfully (Kimi + SenseNova + Bright Data minimum).

---

## 18. Open questions / assumptions

**Assumptions (say the word to change any):**
- Backend = **Python**; storage = **SQLite**; Telegram = **long polling, verified members only**; email = **IMAP polling** of one real Gmail via **App Password**; output = **always bilingual EN+中文**.
- Verification = shared **access code** + admin approve/revoke. Email alert fires on `is_scam and risk_level=="high"` (configurable via `ALERT_THRESHOLD`); recipients = the elder's active guardians.
- No frontend code this phase — contract + stubs + codegen only.

**Need confirmation:**
- Should the **elder also** get a Telegram message on a scam email, or **family only**?
- Bilingual = **English + Simplified Chinese** assumed (not Traditional). OK?
- Sponsor scope: keep all six (tiered, with fallbacks) or trim to the core three?
