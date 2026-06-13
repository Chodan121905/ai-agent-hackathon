# 🛡️ Scam Guardian — How It Works (Plain-English Guide)

> A no-jargon companion to [PLAN.md](PLAN.md). If you're not a programmer, **read this one.**
> It explains *what we're building and how the pieces fit together* using a simple picture: a small
> **security team working inside an office building**.

---

## The one-sentence version

**Scam Guardian is a helper you talk to inside Telegram (a chat app). You forward it a suspicious
message, photo, voice note, or link, and within seconds it tells you — in your own language — "this
is a scam, here's the trick they're using, don't do it." If it's dangerous, it also quietly warns
your family.**

---

## The problem (why this matters)

Older and less tech-savvy people lose the most money to scams. They won't install special apps or
learn new tools — but they *already* use chat apps, and they *already* forward dodgy messages to
their kids asking **"is this real?"**

So instead of building yet another app nobody installs, we put an **expert on the other end of that
exact gesture.** Forwarding a message to one contact is something they already know how to do.

---

## The big idea, as a picture

Think of Scam Guardian as a **building with a security team inside.** A worried message comes in the
front door, gets passed to the right specialist, the team investigates, and a clear answer comes back
out the door — fast.

```
        👵  "Is this message real??"
         │   (forwards it in the chat app)
         ▼
   ┌──────────────────────────────────────────────┐
   │   🏢  THE SCAM GUARDIAN BUILDING               │
   │                                                │
   │   🚪 Front desk      →  receives the message   │
   │   🗂️  Sorter         →  what kind is it?       │
   │   👀 Reader          →  reads text in photos   │
   │   👂 Listener        →  writes down voice notes│
   │   🕵️ Investigator    →  checks suspicious links│
   │   🧪 Safe room       →  opens links safely     │
   │   🧠 Expert detective →  decides: scam or not?  │
   │   📣 Dispatcher      →  picks the cheapest help │
   │   🗃️ Filing cabinet  →  remembers everything   │
   │                                                │
   └──────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
   👵 gets a simple answer    📞 if dangerous, the
      with a 🔴🟡🟢 light        family gets a heads-up
```

---

## What happens when you forward something (the story)

Imagine your mother forwards a text that says *"Your bank account is suspended. Click here to verify."*

1. **It arrives at the front desk.** The chat app (Telegram) hands the message to our building.
2. **The sorter looks at it.** Is this plain text? A photo? A voice recording? A web link? Each goes
   to the right specialist. (This one is text + a link.)
3. **The specialists do their part:**
   - If it were a **screenshot**, the **Reader** would read the words out of the picture.
   - If it were a **voice note**, the **Listener** would write down what was said.
   - Because there's a **link**, the **Investigator** checks it: *Is this website brand new? Is it
     pretending to be the real bank? Have other people reported it as a scam this week?* And if we
     need to actually open the link, the **Safe Room** does it inside a sealed container so nothing
     can reach your phone or our computers.
4. **The expert detective decides.** This is the brain. It reads everything the specialists found and
   judges: *Is this a scam? Which trick are they using?* It recognizes classic tricks — rushing you,
   pretending to be the bank/police, threatening you, asking for passwords or codes, promising prizes.
5. **A simple answer comes back out the door**, written in plain words in *your* language:
   > 🔴 **Scam. Don't click.** They are pretending to be your bank and rushing you so you panic.
   > Real banks never ask you to verify through a link like this.
6. **The filing cabinet remembers it** (without your name) — so we can show everyone *"here are the
   scams going around this week."*
7. **If it's dangerous, your family is warned.** Your son or daughter gets a quiet message: *"Mum is
   being targeted by a scam right now"* — so they can call her immediately. Even if she freezes, the
   safety net catches it.

All of this takes **a few seconds.**

---

## Meet the team (and the real names behind each role)

Every "team member" above is a real piece of technology (several are hackathon sponsors). Here's the
plain-English job each one does:

| Team member | Real name | What it actually does, in plain words |
|---|---|---|
| 🚪 **Front desk** | **Telegram bot** | The chat contact people forward things to. Receives messages and sends answers back. Free, and everyone already has a chat app. |
| 🧠 **Expert detective** | **Kimi k2.6** (an AI) | The brain. Reads the content and decides whether it's a scam, names the trick, and writes the simple explanation in the right language. |
| 👀 **Reader** | **SenseNova U1** (an AI) | Reads the text *inside* a screenshot or photo. Also draws the weekly "scam to watch out for" poster. |
| 👂 **Listener** | **Whisper** (backup: **VideoDB**) | Turns a spoken voice note into written words so the detective can read it. |
| 🕵️ **Investigator** | **Bright Data** | Looks up a suspicious web link: how old the site is, whether it's faking a real company's name, and whether others have flagged it. |
| 🧪 **Safe room** | **Daytona** | A sealed, throwaway room where a dangerous link can be opened safely, far away from your phone and our systems. |
| 📣 **Dispatcher** | **TokenRouter** | Picks the cheapest, fastest AI for each question — easy questions go to a cheap helper, hard ones to the strong one. Keeps costs down. |
| 🧑‍✈️ **Operations manager** | **LangGraph** | Makes sure every step happens in the right order and that specialists can work at the same time. The assembly line that runs the whole investigation. |
| 🏢 **The building itself** | **FastAPI** | The software "office" everything runs inside, and the doorway the future website and phone app will also use. |
| 🗃️ **Filing cabinet** | **Database (Supabase)** | Remembers reports, family connections, and the weekly scam trends. |

> You don't need to remember any of these names. The point is: **each one is a small specialist, and
> the manager makes them work together as a team.**

---

## Three things that make this more than a demo

**1. The family safety net.** Scams work by isolating and panicking the victim. Our answer doesn't
just go to the person being targeted — on a *high-risk* case, it also pings a family member so a real
human can step in. A scam-checker that loops in family is far more powerful than one that doesn't.

**2. Learning without effort.** Once a week, a one-line *"scam of the week"* (with a simple picture)
lands in the chat. People learn to spot scams with zero effort — no course, no app to open.

**3. The "trends" dashboard (why businesses pay us).** Because we (anonymously) remember every scam
forwarded to us, we can show a live picture of *"what scams are spreading right now."* Banks and
phone companies — who are now legally on the hook for scam losses — will pay for that early warning,
and to protect their elderly customers. Families pay for peace of mind.

---

## Why Telegram (and not WhatsApp)?

The original idea used WhatsApp. We're using **Telegram** instead because, for building this quickly:

- It's **free** and takes minutes to set up — no paid phone-messaging account needed.
- It handles **text, photos, voice notes, and links** out of the box.
- Our helper can **start a conversation with a family member** to send the warning (with WhatsApp this
  is harder and costs money).

Everything else about the product — the market, the business model, the pitch — stays exactly the same.
*(One small rule we design around: a family member has to message our bot once first, so it's allowed
to message them back later. We handle that with a simple "pairing code" during sign-up.)*

---

## What we're building **first** (and what comes later)

Think of it like building a restaurant:

- **Now — the kitchen (the "backend").** This is where all the real work happens: receiving messages,
  running the investigation, deciding the verdict, warning the family. We're building this first
  because nothing works without it. The Telegram helper plugs straight into this kitchen.
- **Later — the dining rooms (the "frontends").** Two ways for people to *see* and *manage* things on
  a screen:
  - a **website** (for the trends dashboard that banks would look at), and
  - a **phone app** (built with a tool called Flutter, so one app works on both iPhone and Android).

The important part: we're building the kitchen so that **both dining rooms can be added later without
rebuilding anything.** The kitchen hands out its "menu" (a standard list of what it can do), and the
website and phone app are built automatically from that menu. No wasted work, nothing to redo.

---

## A tiny glossary (only if you're curious)

- **Backend** — the engine room you don't see; does the actual work.
- **Frontend** — the screens you *do* see (website, phone app).
- **AI model** — a computer program trained to understand language, images, or speech. Kimi, SenseNova,
  and Whisper are all AI models doing different jobs.
- **Bot** — an automated account in a chat app that replies for us.
- **Verdict** — the answer card we send back: a 🔴/🟡/🟢 risk light, the trick being used, and what to do.
- **Sandbox** — a sealed, disposable space to open something dangerous safely.

---

> **In one line:** people forward a worry to a chat contact; a coordinated team of AI specialists
> investigates in seconds; a dead-simple answer comes back; and if it's dangerous, the family is
> warned — all inside the app they already use.
