# 🛡️ Scam Guardian — How It Works (Plain-English Guide)

> A no-jargon companion to [PLAN.md](PLAN.md). If you're not a programmer, **read this one.**
> It explains *what we're building and how the pieces fit together* using a simple picture: a small
> **security team working inside an office building**.

---

## The one-sentence version

**Scam Guardian is a helper inside Telegram (a chat app). It protects people in two ways: (1) you can
forward it anything suspicious and it instantly tells you "this is a scam, here's the trick, don't do
it" — in both English and Chinese; and (2) it can quietly watch a person's email inbox and, the moment a scam
email arrives, automatically warn their family — even if the person never noticed it.**

---

## The problem (why this matters)

Older and less tech-savvy people lose the most money to scams. They won't install special apps or
learn new tools — but they *already* use chat apps, and they *already* forward dodgy messages to their
kids asking **"is this real?"**

So instead of building yet another app nobody installs, we put an **expert on the other end of that
gesture** — and we go one step further: we also let the system **watch their inbox and raise the alarm
on its own.**

---

## Two ways it helps

| | How it starts | What happens |
|---|---|---|
| **1. You ask it** *(reactive)* | The person **sends or forwards** anything — a text, screenshot, voice note, or just **pastes a link** — to the bot, like chatting with a helper. | They get a simple answer back in seconds, with a 🔴🟡🟢 light. If it's a link, the **safe room (Daytona)** opens it in a sealed container first to see where it really goes. |
| **2. It watches for you** *(automatic)* | Nobody does anything. A **scam email lands in the inbox** the system is watching. | The system reads it on its own and, if it's a scam, **messages the family** straight away. |

The second one is the safety net: it protects people *even when they don't think to ask.*

---

## The big idea, as a picture

Think of Scam Guardian as a **building with a security team inside.** A worry comes in — either someone
hands it to the front desk, *or* the team spots a dangerous letter arriving in the mailbox by
themselves. The team investigates, and a clear answer (or a warning to the family) goes back out.

```
   👵 "Is this real??"  ──forwards──┐          📧 a scam email quietly arrives ──┐
                                     │                                            │
                                     ▼                                            ▼
   ┌──────────────────────── 🏢  THE SCAM GUARDIAN BUILDING ─────────────────────────┐
   │                                                                                  │
   │   🚪 Front desk        receives forwarded messages (the chat bot)                │
   │   📬 Inbox watcher      keeps checking the email inbox on its own                 │
   │   🗂️  Sorter            figures out what kind of thing arrived                    │
   │   👀 Reader             reads text inside photos                                  │
   │   👂 Listener           writes down what voice notes say                          │
   │   🕵️ Investigator       checks if a link/website is fake or dangerous            │
   │   🧪 Safe room          opens dangerous links in a sealed container               │
   │   🧠 Expert detective   decides: scam or not? names the trick. (the brain)        │
   │   📣 Dispatcher         picks the cheapest/fastest helper for each question       │
   │   📒 Notebook           remembers everything (a simple file on the computer)      │
   │                                                                                  │
   └──────────────────────────────────────────────────────────────────────────────────┘
              │                                              │
              ▼                                              ▼
        👵 simple answer with a light                📞 family gets a heads-up:
           "🔴 Scam — don't click"                      "📧 Mum's inbox just got a scam
                                                          email from 'DBS Security' — call her"
```

---

## Story 1 — you forward something

Your mother forwards a text: *"Your bank account is suspended. Click here to verify."*

1. **It arrives at the front desk** (the chat bot).
2. **The sorter** sees it's text with a link.
3. **The investigator** checks the link: *Is this website brand new? Is it pretending to be the real
   bank? Have others reported it this week?* If the link must actually be opened, the **safe room** does
   it in a sealed container so nothing reaches anyone's phone.
4. **The expert detective** decides it's a scam and names the trick (pretending to be the bank + rushing
   you to panic).
5. **A simple answer comes back**, in her language:
   > 🔴 **Scam. Don't click.** They are pretending to be your bank and rushing you so you panic.
   > Real banks never ask you to verify through a link like this.
6. **The notebook remembers it** (without her name) so we can show *"scams going around this week."*

All in **a few seconds.**

## Story 2 — it catches an email by itself ✨ (new)

Nobody forwards anything. A scam email lands in the inbox the system is watching.

1. **The inbox watcher** notices the new email within a few seconds.
2. It hands the email to the **same expert detective**, who reads the message **and inspects the sender
   address for fakery** — a common trick is an email that *looks* like it's from "DBS Bank" but is really
   sent from a strange address like `alerts@dbs-verify.ru`. It also spots near-identical fake web
   addresses (like `paypa1.com` instead of `paypal.com`).
3. Because it's dangerous, the system **automatically messages the family** through the bot — in **both
   English and Chinese**, and it says **how sure it is**:
   > 📧 **Scam email alert · 92% sure** — Mum's inbox just got an email pretending to be *"DBS Bank"*,
   > but the real sender is `alerts@dbs-verify.ru` — not the real bank. Please call her; tell her not to
   > click or reply.
   > （中文）妈妈的邮箱收到一封假冒"星展银行"的邮件，真实发件地址是 alerts@dbs-verify.ru，并非银行本身。请尽快联系她，不要点击或回复。
4. The family can call her right away — **before** she ever acts on it.

This is the part that protects people who would never have asked in the first place.

---

## Meet the team (and the real names behind each role)

Every "team member" is a real piece of technology (several are hackathon sponsors). The plain-English job:

| Team member | Real name | What it actually does, in plain words |
|---|---|---|
| 🚪 **Front desk** | **Telegram bot** | The chat contact people forward things to, and where answers/alerts come from. |
| 📬 **Inbox watcher** | **Email checker (IMAP)** | Keeps peeking at the email inbox, flags any new scam email on its own, and checks whether the sender address is a **fake pretending to be a real company**. |
| 🧠 **Expert detective** | **Kimi k2.6** (an AI) | The brain — decides scam or not, names the trick, writes the simple explanation. |
| 👀 **Reader** | **TokenRouter** (a vision AI) | Reads text *inside* a screenshot (falls back to Kimi's own eyes if not set up). |
| 👂 **Listener** | **Whisper** (backup: **VideoDB**) | Turns a spoken voice note into written words. |
| 🕵️ **Investigator** | **Bright Data** | Looks up a suspicious link: how old, is it faking a real brand, has it been reported. |
| 🧪 **Safe room** | **Daytona** | A sealed, throwaway space to open a dangerous link safely. |
| 📣 **Dispatcher** | **TokenRouter** | Picks the cheapest/fastest AI per question to keep costs down. |
| 🧑‍✈️ **Operations manager** | **LangGraph** | Runs the whole investigation in the right order, letting specialists work at once. |
| 🏢 **The building** | **FastAPI** | The software "office" everything runs in, and the doorway the future website + phone app will use. |
| 📒 **Notebook** | **SQLite** (a simple file) | Remembers reports, family connections, and weekly trends — just one file, nothing fancy. |

> You don't need to remember any of these. Each is a small specialist; the manager makes them work as a team.

---

## Three things that make this more than a demo

**1. The family safety net.** Scams work by isolating and panicking the victim. Our warnings reach a
family member too — by forwarding *or* by catching a scam email automatically — so a real human can
step in.

**2. Learning without effort.** Once a week, a one-line *"scam of the week"* (with a simple picture)
lands in the chat. People learn to spot scams with zero effort.

**3. The "trends" notebook (why businesses pay us).** Because we (anonymously) remember every scam we
see, we can show a live picture of *"what scams are spreading right now."* Banks and phone companies —
now legally on the hook for scam losses — will pay for that early warning and to protect their elderly
customers. Families pay for peace of mind.

---

## Why Telegram (and not WhatsApp)?

The original idea used WhatsApp. We use **Telegram** because, for building this quickly:
- It's **free** and takes minutes to set up — no paid phone-messaging account.
- It handles **text, photos, voice notes, and links** out of the box.
- Our helper can **start a conversation with a family member** to send the warning.
- For the demo it can run on a normal laptop with **nothing public to set up** — no special web address needed.

Everything about the product — market, business model, pitch — stays the same. *(One small rule we design
around: a family member messages the bot once first, so it's allowed to message them back later. We handle
that with a simple "pairing code" at sign-up.)*

---

## What we're building **first** (and what comes later)

Like building a restaurant:

- **Now — the kitchen (the "backend").** Where all the real work happens: receiving messages, *watching
  the inbox*, running the investigation, deciding the verdict, warning the family. Nothing works without
  it. The Telegram helper plugs straight into this kitchen. For now the kitchen keeps its notes in **one
  simple file** (no big database to set up).
- **Later — the dining rooms (the "frontends").** Two screens for people to see and manage things:
  - a **website** (for the trends dashboard banks would look at), and
  - a **phone app** (built with Flutter, so one app works on both iPhone and Android).

The important part: the kitchen is built so **both dining rooms can be added later without rebuilding
anything.** It hands out a "menu" of what it can do, and the website and phone app are built automatically
from that menu.

---

## A few things we made sure of

These were specifically requested, and the plan now guarantees them:

- **Only approved family can use it.** It's not open to strangers. A new person types a one-time **access
  code** to be let in; everyone else is politely turned away.
- **It tells you *why* and *how sure*.** Every answer shows a confidence like *"92% sure"*, names the trick,
  and explains in plain words — in **both English and Chinese**.
- **Just tell it which language you want.** Say (or type) *"reply in Chinese"* or *"English only"* — in
  normal words, no commands to memorize — and it switches. It starts in both languages until you change it.
- **It listens to voice messages.** Send a voice note and it writes down what you said, then checks it just
  like a typed message — so you can even *speak* a suspicious message or *say* "use English".
- **It catches fakes, not just bad wording.** It checks the sender's real email address and web links for
  impersonation — fake "bank" senders, look-alike addresses, and disguised links.
- **It runs as one program on your laptop.** Start it once and it does everything — answers messages *and*
  watches the inbox — for as long as it's running. Close it, and it stops. Nothing to host on the internet.
- **You connect your own Gmail, safely.** You give it a special "app password" for a throwaway demo Gmail
  (step-by-step instructions are in the technical plan). Then you can demo by sending a fake phishing email
  to that inbox and watching the family get warned.

---

## A tiny glossary (only if you're curious)

- **Backend** — the engine room you don't see; does the actual work.
- **Frontend** — the screens you *do* see (website, phone app).
- **AI model** — a program trained to understand language, images, or speech (Kimi, Whisper).
- **Bot** — an automated account in a chat app that replies for us.
- **Inbox watcher / IMAP** — the part that keeps checking the email inbox for new mail.
- **Verdict** — the answer card: a 🔴/🟡/🟢 light, the trick used, and what to do.
- **Sandbox** — a sealed, disposable space to open something dangerous safely.

---

> **In one line:** people forward a worry — *or the system spots a scam email on its own* — a coordinated
> team of AI specialists investigates in seconds, a dead-simple answer comes back, and if it's dangerous
> the family is warned — all inside the app they already use.
