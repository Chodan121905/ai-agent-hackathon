# 🛡️ Scam Guardian
### WhatsApp-native scam protection for families — Agent Forge Hackathon

> **The protection your parents will actually use — because it lives in the app they already have.**

---

## The 30-second pitch (what judges hear)

Elderly and non-tech-savvy people lose the most money to scams, yet they won't install apps or learn new tools. But they all use WhatsApp, and they already forward suspicious messages to their kids asking *"is this real?"* **Scam Guardian puts an AI on the other end of that gesture.** Forward a text, screenshot, voice note, or link to one WhatsApp contact and get an instant, dead-simple verdict in your own language — and your adult child gets alerted the moment you're targeted. Banks and telcos are now legally liable for these losses, so they'll pay to deploy it; families pay for peace of mind.

---

## Why this is a real product, not a demo

### The market is huge — and the most vulnerable users are underserved
- Singapore lost **~S$913 million** to scams in 2025, down from a **record S$1.1 billion in 2024** — over **S$3.4 billion lost since 2019**. (SPF Annual Scams & Cybercrime Briefs)
- **The elderly make up a small share of victims but lose the most per victim of any age group.** They are the highest-value-at-risk segment and the hardest to protect with apps.
- **82% of scam cases are "self-effected transfers"** — victims are *manipulated into transferring the money themselves*, not hacked. This is a **human-judgment problem**, so the right place to intervene is at the moment a person decides to act — exactly where a simple, in-context verdict helps.
- Top scam types hitting this group: **government-official impersonation** (fake police/IRAS) and **phishing** — the calls and messages elders receive daily.

### Why now — the regulatory tailwind makes the business model real
- Singapore's **Shared Responsibility Framework (SRF)**, effective **16 Dec 2024**, makes **banks and telcos financially liable** for covered phishing-scam losses if they breach their anti-scam duties (a "waterfall": bank → telco → consumer).
- Revised **E-Payments User Protection Guidelines** require banks to **detect and block suspicious transactions at all times** (from 16 Jun 2025).
- This is a **global wave**: UK (APP-fraud reimbursement, Oct 2024), Australia (Scams Prevention Framework), US (proposed), Hong Kong (consultation). The market isn't just Singapore.

**Translation:** banks and telcos now have a direct financial and legal reason to prevent scams reaching their customers — especially elderly ones who lose the most. That is the wedge.

### Distribution that actually works
- **Wedge user:** the adult child — motivated, tech-capable, already worried, willing to pay.
- **Channel:** WhatsApp — zero install, zero learning, gestures elders already use (forwarding, voice notes).
- **Growth loop:** every adult child onboards their parents; families share it in family chats. Viral within the unit that cares most.

### Business model
1. **B2C freemium** — free basic checks; family plan (multiple elders, priority alerts, voice support) for a few dollars/month.
2. **B2B2C (the big one)** — banks, telcos, and insurers white-label it for elderly customers to cut SRF liability and meet detection duties.
3. **Scam-intelligence feed** — anonymised, aggregated "what's trending this week" data sold to banks/telcos/regulators as an early-warning product.

### Moat
- **Data flywheel** — every forwarded scam sharpens detection and feeds the intelligence product.
- **Network effects** — value grows as more family members join.
- **Complements ScamShield, doesn't compete** — the government app blocks *known* numbers/SMS; Scam Guardian handles the **gray-area, multilingual, voice, and screenshot cases that need human-style judgment**, plus the family loop.

---

## What it does (the product)

The elder forwards the suspicious thing to **one WhatsApp contact** and gets a reply in seconds:

| Input | Example | Response |
|---|---|---|
| Text / SMS | "Your DBS account is suspended, verify now" | 🔴 *"Scam. Don't click. Real banks never ask this."* |
| Screenshot | Fake bank login, phishing chat | Reads the image, returns a verdict |
| Voice note | *"Someone called saying I won money — real?"* | Transcribes, explains in plain language |
| Link | A suspicious URL | Checks the domain, returns a verdict |

Replies are in the user's language (**Mandarin / Malay / Tamil / English**), calm and simple, naming the trick.

**The family loop** — the adult child is connected as guardian. On a high-risk hit, *they* get pinged too (*"Dad is being targeted by a scam right now"*) so they can call immediately. Even if the elder freezes, the safety net catches it.

**Passive learning** — a one-line *"scam of the week"* lands in the elder's chat, so they learn with zero effort.

---

## Architecture & sponsor mapping

```
WhatsApp (forwarded text / screenshot / voice note / link)
        │
        ▼
   Intake & router
        ├── screenshot ──► SenseNova U1 (reads image → text)
        ├── voice note ──► VideoDB (transcribes audio → text)
        ├── link ────────► Bright Data (domain age, brand impersonation,
        │                              this-week scam cross-reference)
        │              └──► Daytona (safely opens the link in a sandbox)
        └── text ────────────────────────────────► (straight through)
                                │
                                ▼
                  Kimi k2.6 — the brain (agent swarm)
              one agent reads content · one verifies via tools
                                │
                                ▼
                Verdict JSON → simple multilingual reply
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                     ▼
     Reply to the elder                 If high risk: alert the family
        (TokenRouter handles model routing / cost throughout)
```

| Sponsor | Role |
|---|---|
| **Kimi k2.6** | Tactic detection + plain-language multilingual verdict; agent swarm (read + verify in parallel) |
| **SenseNova U1** | Reads forwarded screenshots; generates the visual "scam of the week" card |
| **VideoDB** | Transcribes voice notes (the elder differentiator) |
| **Bright Data** | Verifies links and keeps detection current with this week's real SG scams |
| **Daytona** | Safe sandbox to open suspicious links and run the pipeline |
| **TokenRouter** | Cost/latency routing across models |

---

## One-day build plan

Channel: **Twilio WhatsApp sandbox** — gives you a real WhatsApp number judges can message within minutes. (Production path: Meta WhatsApp Business API.)

- **Hr 0–1 — Setup.** Claim all sponsor credits now. Get the Twilio WhatsApp number live and a Kimi "hello world" working. Round-trip one text → Kimi → WhatsApp reply.
- **Hr 1–2 — The brain (highest priority).** Text → Kimi → strict JSON verdict → formatted WhatsApp reply. Nail the prompt and the simple multilingual output. This is the product's soul — don't move on until it's reliable.
- **Hr 2–3 — Screenshots.** SenseNova reads forwarded images into the pipeline.
- **Hr 3–4 — Links.** Bright Data domain/brand checks + this-week scam cross-reference; optional Daytona safe-open.
- **Hr 4–5 — Voice notes.** VideoDB transcription → pipeline. Big differentiator for elders who prefer talking.
- **Hr 5–6 — The family loop.** Link a guardian (simple onboarding, e.g. reply `ADD <name> <number>`); on high risk, fire a WhatsApp/SMS alert to them.
- **Hr 6–7 — The "this is a company" layer.** A simple **Scam Intelligence dashboard** (web page) showing trending scams aggregated from forwards — your B2B data product. This is what signals *real company* to judges.
- **Hr 7–8 — Demo prep.** Real WhatsApp number judges can text, three live examples (text / screenshot / voice), the family alert firing, and the 2-minute pitch with market + business model.

**De-risking:** the riskiest piece is voice-note transcription. If it's shaky on the day, demo the text + screenshot + link paths solidly and present voice as the "and it handles voice too" moment with a pre-recorded clip.

---

## The demo that signals "real company"

Judges decide on the problem framing and the live demo. Run it in this order (2–3 min):

1. **Problem (10s).** *"Singaporeans lost S$913 million to scams last year. The elderly lose the most per victim — and four in five victims were tricked into transferring the money themselves."* → it's a human-judgment problem.
2. **Insight (10s).** *"Elders won't install apps. But they all use WhatsApp and already forward dodgy messages to their kids. We put an AI on the other end."*
3. **Live demo (60–90s).** Have a judge text the real WhatsApp number. Forward a phishing SMS → instant simple verdict. Send a screenshot → SenseNova reads it. Send a voice note → transcribed + verdict. High-risk → a family phone across the room buzzes.
4. **Business (30s).** *"Banks and telcos are now legally liable for phishing-scam losses under MAS's Shared Responsibility Framework and must detect suspicious transactions. They'll pay to deploy this to elderly customers and cut their liability. Families pay for peace of mind."* → show the dashboard → *"and the aggregated scam feed is a real-time intelligence product. The same regulations are hitting the UK, Australia, and the US — this is global."*
5. **Close (10s).** *"Scam Guardian — the protection your parents will actually use, on the app they already have."*

---

## The Kimi brain (paste-ready)

System prompt for `kimi-k2.6`:

```
You are Scam Guardian, protecting elderly and non-tech-savvy users from scams.
A user has forwarded you a message, screenshot text, transcribed voice note, or link.
Assess it for scam risk.

Detect these manipulation tactics:
- Urgency / time pressure ("act now", "account will be closed")
- Authority impersonation (bank, police, IRAS, MOM, government, a known company)
- Threat / fear (arrest, fines, account suspension, legal action)
- Secrecy ("don't tell anyone", "keep this confidential")
- Unusual payment (gift cards, crypto, transfer to an unknown/personal account, "verification" fee)
- Requests for OTP, passwords, PINs, banking login, or ID/personal details
- Too-good-to-be-true (lottery, prize, guaranteed high returns, unexpected refund)
- Sender/link mismatch (display name != real domain, lookalike domains, link shorteners)
- Emotional leverage (family in danger, romance, sympathy)

Output ONLY valid JSON in this schema:
{
  "risk_level": "high" | "medium" | "low",
  "is_scam": true | false,
  "tactics": [ "..." ],          // named tactics detected; [] if none
  "explanation": "...",          // 1-2 short sentences, plain words a 70-year-old understands, in the user's language
  "action": "...",               // the single clearest next step
  "alert_family": true | false   // true only when risk_level is "high"
}

Rules:
- Detect the user's language from the input and write "explanation" and "action" in it
  (support English, Mandarin, Malay, Tamil).
- Stay calm and simple. Name the trick in everyday terms
  (e.g. "They are rushing you so you do not think. That is a scam trick.").
- Never tell the user to click, reply, call back, or pay to "verify".
- If unsure, lean to "medium" and tell them to check with family or call the
  official number on the back of their bank card.
- Output nothing outside the JSON.
```

---

## Success criteria (real signal, not vanity)

- [ ] A judge can text the real WhatsApp number and get a correct, simple verdict live
- [ ] At least three input types work end-to-end (text, screenshot, voice note)
- [ ] The verdict names the *tactic* in plain language, in more than one language
- [ ] The family alert fires on a high-risk case during the demo
- [ ] The pitch states clearly **who pays and why** (SRF liability + family peace of mind)
- [ ] At least three sponsors integrated meaningfully (Kimi + SenseNova + Bright Data minimum)

---

## Sources for your deck (all current, citable)

- Singapore Police Force — Annual Scams & Cybercrime Brief 2024 (record S$1.1B; elderly highest loss per victim; 82.4% self-effected transfers) and 2025 (~S$913M).
- MAS / IMDA — Shared Responsibility Framework for phishing scams (effective 16 Dec 2024); revised E-Payments User Protection Guidelines (detect/block duty from 16 Jun 2025).
- Comparable frameworks: UK APP-fraud reimbursement (Oct 2024), Australia Scams Prevention Framework, US proposed legislation, Hong Kong consultation.
