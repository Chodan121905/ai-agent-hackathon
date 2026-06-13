# Scam Guardian — Backend

One Python process that runs **everything**: the FastAPI API, the real Telegram bot
(long polling), and the autonomous Gmail monitor — all driving one multi-phase LangGraph
agent. See [../PLAN.md](../PLAN.md) for the full design and [../PLAN-SIMPLE.md](../PLAN-SIMPLE.md)
for the plain-English version.

## Quickstart

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1            # mac/linux: . .venv/bin/activate
pip install -e .                      # core deps
copy .env.example .env                # then fill in the keys below

python -m app                         # ONE process = API + Telegram bot + email monitor
#   http://localhost:8000/docs   ·   Ctrl+C stops everything
```

Optional extras (install only what you demo):

```powershell
pip install -e ".[stt]"      # faster-whisper for voice notes (needs ffmpeg on PATH)
pip install -e ".[videodb]"  # VideoDB STT path
pip install -e ".[daytona]"  # Daytona safe-link sandbox
pip install -e ".[dev]"      # pytest + ruff
```

## What you need to provide (`.env`)

| Key | What | Where |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Real bot token | `@BotFather` → `/newbot` |
| `ACCESS_CODE` | Shared code members type once to be allowed in | you choose |
| `ADMIN_TELEGRAM_ID` | Your numeric Telegram id (auto-verified, can `/approve`) | message `@userinfobot` |
| `LLM_API_KEY` | Kimi k2.6 key (or TokenRouter `tr_...`) | platform.kimi.ai |
| `EMAIL_IMAP_USER` / `EMAIL_IMAP_PASSWORD` | A **throwaway** Gmail + 16-char App Password | see PLAN.md §7.4 |

Sponsor keys (`SENSENOVA_*`, `VIDEO_DB_*`, `BRIGHTDATA_*`, `DAYTONA_*`) are optional — each
integration has a built-in fallback, so the app boots and runs without them.

### Connecting Gmail (App Password — do once)
1. Google account → **Security → turn on 2-Step Verification**.
2. **myaccount.google.com/apppasswords** → create "ScamGuardian" → copy the 16-char password.
3. Gmail **Settings → Forwarding and POP/IMAP → Enable IMAP → Save**.
4. Put the address + app password into `.env`. Use a **demo** account, not a personal one.

## Graceful degradation (important)

- **No `LLM_API_KEY`** → the agent uses a **deterministic fallback** verdict. The *email
  impostor detection* (display-name mismatch, look-alike/punycode domains, freemail-as-company,
  Reply-To/auth failures) still works and still flags scams as **high risk** with bilingual
  output — that's the headline autonomous feature. But judging *free-text wording* (e.g. a
  forwarded SMS with no bad sender) needs the Kimi brain, so add the key for full coverage.
- **No `TELEGRAM_BOT_TOKEN`** → the bot is skipped; the API + email monitor still run.
- **No Gmail** → the email monitor is skipped; the bot + API still run.

## Demo the autonomous path

1. Fill `.env` (Telegram token, access code, Gmail app password, LLM key).
2. `python -m app`.
3. In Telegram: `/verify <ACCESS_CODE>` yourself, then `/verify` a second "family" account.
   On the elder account run `/invite`, then on the family account `/guardian <code>`.
4. Send a phishing email to the monitored Gmail → within ~20s the family **and** the elder
   get a bilingual alert naming the real sender, the trick, and a confidence %.

## Tests

```powershell
pytest -q          # forensics + full-graph (runs offline, no keys needed)
```

## Run order of the milestones
M0 scaffold · M1 brain · M2 bot+verify+language · M3 family loop · M4 autonomous email +
impostor detection · M5 screenshots · M6 links+Daytona · M7 voice · M8 trends · M9 codegen ·
M10 polish. All implemented; M5–M7 light up as you add the relevant keys / ffmpeg.
