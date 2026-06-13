# 🛡️ Scam Guardian
### Telegram-native scam protection for families — Agent Forge Hackathon

> **The protection your parents will actually use — because it lives in the app they already have.**

Companion docs: [PLAN.md](PLAN.md) (technical build plan) · [PLAN-SIMPLE.md](PLAN-SIMPLE.md) (plain-English) · [backend/README.md](backend/README.md) (run it).

---

## The 30-second pitch

Elderly and non-tech-savvy people lose the most money to scams, yet they won't install apps or learn new tools. But they already use chat apps and already forward dodgy messages to their kids asking *"is this real?"* **Scam Guardian puts an AI on the other end of that gesture — and goes one step further by watching their inbox for them.**

It works **two ways**:
1. **You ask it.** Forward a text, screenshot, voice note, or link to one Telegram contact → instant, dead-simple verdict (🔴 scam / 🟡 unsure / 🟢 safe) with a **confidence %**, the **named trick**, and **what to do** — in the user's language.
2. **It watches for you.** It quietly monitors a real email inbox (**including Spam**) and, the moment a scam email arrives, **automatically warns the family** — even if the person never noticed.

Banks and telcos are now legally liable for these losses, so they'll pay to deploy it; families pay for peace of mind.

---

## What it does (the product)

| Input | Example | Response |
|---|---|---|
| Text / SMS | "Your DBS account is suspended, verify now" | 🔴 *"Scam · 96% — they pretend to be your bank and rush you. Don't click."* |
| Screenshot | Fake bank login, phishing chat | Reads the image (OCR), returns a verdict |
| Voice note | *"Someone called saying I won money — real?"* | Transcribes it, explains in plain language |
| Link | A suspicious URL | Opens it **safely in a sandbox**, checks the domain, returns a verdict |
| **Email (automatic)** | A phishing email lands in the inbox | **Family is alerted automatically** with the sender + why + confidence |

Plus:
- **Catches every shape of phishing**, not just bad wording: fake/impostor sender addresses, display-name vs real-address mismatch, look-alike & punycode domains (`paypa1.com`), freemail-pretending-to-be-a-bank, Reply-To / SPF / DKIM / DMARC failures, and disguised links.
- **The family safety net.** Guardians (and the elder) are alerted on a real threat, so a human can step in *before* money moves.
- **A friendly companion.** Between checks it just chats — and **remembers each person** (including the scams it has checked for them), so it can answer follow-ups like *"what if it's real?"*.
- **Speaks one language at a time**, switchable with a tap (**Change to English** / **改用中文**) or by just asking — while still understanding input in any language. English + 简体中文 (Malay/Tamil on request).
- **Verified members only** — a shared access code admits family; strangers are turned away.

---

## Why this is a real product, not a demo

### The market is huge — and the most vulnerable users are underserved
- Singapore lost a record **~S$1.1 billion to scams in 2024**; **>S$3.4 billion since 2019**.
- **The elderly lose the most per victim** of any age group — the highest-value-at-risk, hardest-to-protect segment.
- **82% of cases are "self-effected transfers"** — victims are *manipulated into paying themselves*. It's a **human-judgment problem**, so the right place to intervene is the moment a person decides to act.

### Why now — the regulatory tailwind
- Singapore's **Shared Responsibility Framework (SRF)** (effective **16 Dec 2024**) makes **banks and telcos financially liable** for covered phishing-scam losses.
- Revised **E-Payments User Protection Guidelines** require banks to detect/block suspicious transactions.
- This is a **global wave**: UK (APP-fraud reimbursement), Australia, US (proposed), Hong Kong.

**Translation:** banks and telcos now have a direct financial reason to keep scams away from customers — especially the elderly. That's the wedge.

### Business model
1. **B2C freemium** — free checks; a family plan (multiple elders, priority alerts) for a few dollars/month.
2. **B2B2C (the big one)** — banks/telcos/insurers white-label it for elderly customers to cut SRF liability.
3. **Scam-intelligence feed** — anonymized, aggregated "what's trending this week," sold to banks/telcos/regulators.

### Moat
- **Data flywheel** — every checked scam sharpens detection and feeds the intelligence product.
- **Network effects** — value grows as more family members join.
- **Complements ScamShield** — it handles the gray-area, multilingual, voice, screenshot, and family-loop cases that need human-style judgment.

---

## How it works (the agentic workflow)

One process runs everything; **one AI brain** is reached through several doors (Telegram, the email monitor, a REST API). The brain is a **multi-phase LangGraph agent**:

```
 Telegram (forward / chat / voice / photo / link)        Real Gmail inbox + Spam
                       │                                          │
                       ▼                                          ▼  (poll ~20s)
        ┌──────────────────────── LangGraph agent (one brain) ────────────────────────┐
        │ intake → route → extract (OCR · voice · link sandbox · email forensics)      │
        │   → intent (chat? scam-check? language switch?)                              │
        │       chat ─────────► companion (per-person memory)                          │
        │       check ────────► verify (deterministic forensics) ∥ synthesize (Kimi)   │
        └──────────────────────────────────────────────────────────────────────────────┘
                       │                                          │
                       ▼                                          ▼
            reply (verdict + buttons)              if scam → alert family + elder
```

**Two principles:** (1) **deterministic-first** — hard forensic flags (fake sender, look-alike domain, auth failure) can mark something high-risk on their own, so detection doesn't depend on the model; (2) **one brain, many doors** — every entry point runs the same graph and produces the same `Verdict`.

---

## Architecture & sponsor mapping

| Sponsor | Role | Status |
|---|---|---|
| **Kimi k2.6** (Moonshot) | The brain — intent routing, companion chat, the bilingual verdict | 🟢 load-bearing |
| **Daytona** | Opens suspicious links in a disposable sandbox to resolve the real destination | 🟢 active |
| **VideoDB** | Transcribes voice notes to text | 🟢 active |
| **Bright Data** | Domain age + scam-reputation lookups for links | 🟡 called (limited by zone setup) |
| **TokenRouter** | Screenshot OCR (vision); falls back to Kimi-vision if unset | ⚪ wired (Kimi-vision active) |

Everything runs as **one local process** — no servers to host, no public URL. (SenseNova from the original plan was dropped; OCR moved to TokenRouter/Kimi-vision.)

---

## Tech stack

- **Python 3.12**, **FastAPI** (auto OpenAPI 3.1 contract for future web + Flutter clients)
- **LangGraph** multi-phase agent · **Kimi k2.6** via OpenAI-compatible API
- **python-telegram-bot** (long polling — no webhook/tunnel)
- **IMAP** (stdlib) for autonomous email monitoring (Inbox + Spam)
- **SQLite** (SQLModel) for reports/trends · per-person memory files
- Sponsor clients: Daytona, VideoDB, Bright Data, TokenRouter

---

## Run it

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env        # fill in the keys below

python -m app                 # OR double-click run.bat in the repo root (auto-restarts)
#   http://localhost:8000/docs   ·   Ctrl+C stops everything
```

**Keys you provide in `backend/.env`:** `TELEGRAM_BOT_TOKEN` (from @BotFather), `ACCESS_CODE`, `LLM_API_KEY` (Kimi/Moonshot), and a throwaway Gmail + 16-char **App Password** (`EMAIL_IMAP_USER` / `EMAIL_IMAP_PASSWORD`, see [PLAN.md §7.4](PLAN.md)). Sponsor keys (`DAYTONA_API_KEY`, `VIDEO_DB_API_KEY`, `BRIGHTDATA_API_TOKEN`, `TOKENROUTER_API_KEY`) are optional — each has a fallback.

**Demo flow:**
1. In Telegram, message the bot → `/verify <ACCESS_CODE>`.
2. Forward a phishing text or paste a link → instant verdict (with live progress + language buttons).
3. Link a "family" account: elder runs `/invite` → guardian runs `/guardian <code>`.
4. Send a phishing email to the watched Gmail → ~15–20s later the family **and** elder get a bilingual alert naming the sender + why + confidence — **without anyone forwarding it.**
5. Tap **改用中文** → the same verdict, fully in Chinese.

---

## Success criteria (what to look for in the demo)

- [ ] One command (`python -m app` / `run.bat`) boots a **real** Telegram bot + email monitor.
- [ ] **Verified-only:** a stranger is refused; `/verify <code>` admits a member.
- [ ] A forwarded scam returns a correct verdict — **risk light, confidence %, named tactic, plain-language why** — in one language, switchable by button.
- [ ] **Autonomous + impostor detection:** a phishing email (spoofed sender / look-alike domain) sent to the inbox triggers a **family alert within ~20s**, naming the real sender — without anyone forwarding it.
- [ ] A **voice note** is transcribed and understood; a **link** is opened in a sandbox before the verdict.
- [ ] The companion **remembers** a checked scam and answers a follow-up about it.
- [ ] ≥3 sponsors integrated meaningfully (Kimi + Daytona + VideoDB, plus Bright Data).

---

## Sources (citable)

- Singapore Police Force — Annual Scams & Cybercrime Brief 2024 (record S$1.1B; elderly highest loss per victim; ~82% self-effected transfers).
- MAS / IMDA — Shared Responsibility Framework for phishing scams (effective 16 Dec 2024); revised E-Payments User Protection Guidelines.
- Comparable frameworks: UK APP-fraud reimbursement, Australia Scams Prevention Framework, US proposed legislation, Hong Kong consultation.
