# HERMES DEMO — EMMANUEL LOWINGER MEETING PLAN

**Date:** ~2026-04-22 (confirm)
**Attendees:** Conaugh McKenna, Adon, Emmanuel Lowinger
**Duration:** 45–60 minutes
**Stakes:** High. This is the commit meeting.

---

## Meeting Objective

Get Emmanuel to sign the 14-day free trial agreement before he leaves the room. Show him Hermes is real, alive, and running on a laptop he can touch — not a pitch deck, not a promise, a working teammate.

---

## Pre-Meeting Prep Checklist

### Night Before
- [ ] Laptop charged, charger packed, second charger in bag
- [ ] Ollama running locally, model pre-loaded (no cold-start lag)
- [ ] Hermes v0.1.0 pulled from `CC90210/hermes`, mock mode verified
- [ ] `demo.bat` tested end-to-end — confirm <1 second runtime
- [ ] 3 sample POs pre-loaded in `/inbox/` (1 clean, 1 with a typo, 1 with multiple line items)
- [ ] Backup: mock mode ready if Ollama hiccups. NEVER debug live.
- [ ] Terminal font size cranked to 18pt. He needs to read it from across the table.
- [ ] Audit log file open in a second window
- [ ] Slides loaded but minimized — slides are backup, not primary
- [ ] WiFi hotspot ready in case venue WiFi is trash
- [ ] Phones on silent. Not vibrate. Silent.
- [ ] **If Emmanuel asks "do you handle ASN/labels?" the answer is YES — we just haven't built it yet, but it's in the roadmap. Open the BUILD_PLAN.md Phase 2b on the laptop and show him. Never say "not yet" without showing the plan.**

### Day Of
- [ ] Trial agreement printed, 2 copies, signed by Conaugh McKenna already
- [ ] Pricing one-pager printed, 2 copies (updated with full compliance stack pricing)
- [ ] Shopify case study numbers memorized cold (no looking at phone)
- [ ] Bennett case study: $3K MRR, 158 members, 100% retention, 63% engagement
- [ ] Whiteboard markers working (test before meeting — 3 colors)
- [ ] Arrive 15 minutes early. Set up in silence. Be there when he walks in.
- [ ] Eat before. Caffeinated, not jittery.

---

## Agenda (45–60 min)

| Time | Block | Goal |
|------|-------|------|
| 2 min | Welcome + energy match | Match his intensity, no weather talk |
| 3 min | "What you said last time" | Play back his own words |
| 3 min | The Chargeback Math | Anchor the financial case before the demo |
| 8 min | Live demo | Show Hermes actually working |
| 3 min | Architecture in 90 seconds | Plain English, no jargon |
| 5 min | Shopify case study | The closest match to his business |
| 10 min | Trial terms + pricing | Put the number on the table |
| 5 min | IDE Hermes reveal | The "he's on your team" moment |
| 10 min | Discovery questions | Lead with Section 0 (compliance), then technical |
| 5 min | Close | Commit, group chat, go-live date |

---

## Welcome + Energy Match (2 min)

No small talk. No "how's Miami." He said every moment counts — act like it.

**Opening line (Conaugh):** "Emmanuel. Good to see you. We built what we said we'd build. Let me show you."

Sit down. Open the laptop. That's it. He'll feel the pace immediately.

---

## "What You Said Last Time" (3 min)

Before the demo, spend 60 seconds replaying his own words. This earns the next 40 minutes.

**Script:**
> "Last time you said three things. One — you need to see this work, because it sounds like sci-fi. Two — you invest in people, not code. Three — someone with capital will copy this in a month, so speed matters. We heard all of it. The next 45 minutes is us proving we listened."

Then: **The Chargeback Math.** Don't go to the demo yet.

---

## The Chargeback Math (3 min)

This is the real anchor. Time savings is a nice-to-have. Chargeback prevention is a financial emergency.

**Script:**
> "Before we run the demo, I want to ask you something. What's your current ASN process — the Advance Ship Notice you send Walgreens before a truck leaves? Is that bulletproof right now, or is that one of those things your team does manually when they remember?
>
> When did you last get hit by a Walgreens fine? The Cost Recovery Program — it runs automatically, every week, on their SAP system. It's not a person making a judgment call. It's a formula.
>
> [Let him answer. Write the number down if he gives one.]
>
> The industry exposure for a shop your size is fifty to a hundred and fifty thousand dollars a year. Not because of bad products or bad relationships — because of a late ASN file, or because the SSCC number on the carton label didn't match the ASN exactly. That's it. A timing issue and a data mismatch.
>
> Hermes fixes both. That's actually the highest-value piece of this. Anyone can parse a PO. Not many can keep you compliant with Walgreens automatically."

Pause. Then go to the demo.

---

## The Demo Script (8 min)

### Windows to Have Open
1. **Terminal 1** — Hermes root directory, ready to run `demo.bat`
2. **Terminal 2** — tail of audit log
3. **File Explorer** — `/inbox/` folder with the 3 sample POs visible
4. **Text editor** — one sample PO email open so he can see the "input"

### Opening Line
> "This is Hermes. He's running on this laptop right now — no cloud, no servers, nothing leaving this machine. Watch the timestamps. I'm going to drop a purchase order in his inbox, and you're going to see him handle it."

### The Sequence

**Step 1 — Show the input.**
Open the sample PO email. Read it out loud quickly:
> "Okay — this is the kind of email your team gets. PO number, three line items, shipping address, terms. Right now, this is where your 70% copy-paste starts."

**Step 2 — Run the demo.**
```
demo.bat
```
Narrate as it runs (it's going to be fast, so narrate DURING, not after):
> "He's reading the email. He's extracting the PO number. He's parsing the line items — three of them. He's validating against the customer record. He's pushing it into A2000 — right now we're in mock mode, but this is the exact same call we'll make to your real A2000. He's pulling the generated invoice number back. He's drafting the confirmation email. Done."

**Step 3 — Show the output.**
> "Notice: three line items extracted, totals calculated, invoice number generated, confirmation email drafted, audit log written. All in under a second. All on this machine."

**Step 4 — Show the audit log.**
Switch to terminal 2.
> "This is every action he took. Timestamped. Traceable. If he ever does something you don't like, you see it here — and you tell him to stop doing it. He learns."

**Step 5 — The money line.**
> "That loop right there — email in, PO parsed, A2000 entry, invoice out — that's the loop your team is doing 100 times a week by hand. Hermes does it while you're asleep."

### If Ollama Breaks or Lags
Don't panic, don't apologize, don't debug. Switch to mock mode silently:
> "Let me run it in mock mode so you see the full pipeline at speed — the local model is the same thing, just with actual parsing instead of fixtures."

He will not notice. Move on.

---

## Architecture in 90 Seconds (3 min)

Whiteboard. Three boxes. No jargon.

1. **Inbox** → "He watches your Outlook. Sees a PO come in."
2. **Brain** → "He reads it. Local AI model on your machine. Never phones home."
3. **A2000 + Compliance Out** → "He enters it. Sends the ASN. Prints the labels. Pulls the invoice. Sends the confirmation."

That's it. Under the boxes write: **"Encrypted. Audited. Local. Yours."**

Add a fourth box on the right side: **"Dispute Tracker"** — "He watches for Walgreens fines, tracks the 4-week window, and drafts the dispute before the money is gone."

If he asks how the brain works, one sentence: "It's an open-source language model running on your hardware — same family as ChatGPT, but private and offline."

---

## Shopify Agent Case Study (5 min)

This is the answer to "who have you scaled that looks like me?"

**Script:**
> "Closest match we have to your business is a Shopify operator we built an agent for. Different industry — e-commerce, not wholesale — but same bones. Orders coming in, inventory checks, customer comms, invoicing. We replaced roughly 20 hours of weekly manual work per operator. The agent ran quietly for the first two weeks — we watched every action — and by week three the owner stopped reviewing every output because he trusted it. That's the arc we're pitching you: two weeks of supervised trust-building, then he's just part of your team."

Add Bennett as the track-record proof:
> "On the community side, we run an operation at $3,000 MRR with 158 members and 100% retention. That's us doing long-term client work, not one-and-done. We don't disappear."

---

## Trial Terms + Pricing (10 min)

Put the page on the table. Do not apologize for the number. Do the math for him.

### What We Propose

- **14-day free trial.** Starts the day Hermes is installed on his machine.
- **What's included:** Full email → PO → A2000 → invoice loop. Audit logs. Escalation emails. Our hands on it the whole time.
- **What we need from him:** A2000 test environment access, 10 sample POs, 2 check-in calls (day 3, day 10).
- **Success criteria:** 80%+ of POs processed end-to-end without human intervention. Zero wrong-customer errors. Every mistake logged and reviewed.

### Post-Trial Pricing (recommended anchor)

**$1,500/month base retainer** + **$0.50 per PO processed** after the first 1,000/month.

At his likely volume (~400 POs/week = ~1,600/month):
- Base: $1,500
- Overage: 600 POs × $0.50 = $300
- **Total: ~$1,800/month**

### The Real ROI Math — Lead With Chargebacks, Not Time

> "Here is how the math actually works. The $50,000 to $150,000 a year in Walgreens fines — that's the floor argument. That's the number before we count a single hour of labor saved. If Hermes prevents even one missed ASN per week — one shipment that doesn't generate a fine — at 1% to 5% of invoice value, you're looking at hundreds of dollars recovered per event.
>
> Time savings is the bonus on top. If you process 20 orders a day at 15 minutes each, that's 5 hours of daily manual work gone permanently. One AP hire is $4,000 to $5,000 a month loaded. Hermes runs for $1,800, 24/7, and never generates a late ASN.
>
> The trial is free. You don't pay us a dollar until you've seen him work for two weeks."

### Exit Clause
30-day cancellation, no lock-in, he owns his data, we export everything on request. Say this unprompted — it kills the biggest objection before he raises it.

---

## The IDE Hermes Reveal (5 min)

This is the kicker. Don't lead with it — he'll think it's bloat. Drop it AFTER he's seen the pipeline work.

**Script:**
> "One more thing. The pipeline we just showed you — that's the background Hermes. He runs 24/7. Quietly. But once you've trusted him for a week or two, we turn on the front door. You get Hermes in your IDE, on your machine, and you can just talk to him."
>
> "Watch — my co-founder does this every day with our own agent. He types: 'Hey Bravo, status on the Lowinger account.' Gets an answer. 'Draft a quote for 500 units at 12% margin.' Done. 'Pull every PO from Walgreens last 30 days.' Done."
>
> "That's you, six weeks from now. You're at a trade show. You pull out your laptop, type 'Hermes, what's our exposure on the outstanding Walgreens orders?' He tells you. You ask him to draft three follow-up emails. He drafts them. You review and send."
>
> "He's not a tool. He's a team member."

Then stop. Let that hang.

---

## Discovery Questions (10 min — MUST get answered)

**Lead with Section 0 (compliance) before technical questions.** The chargeback math is already on the table — the first question lands naturally.

Do not leave without these answers. Write them down on paper in front of him — he'll feel the weight.

**Compliance (Section 0 — ask first):**
1. **Walgreens chargeback exposure** — annual or quarterly estimate. Do they track this number?
2. **ASN process today** — how is the 856 getting sent? Manual via SupplierNet, EDI broker, or not at all?
3. **EDI VAN / broker** — SPS Commerce, TrueCommerce, CrossBridge? Monthly cost?
4. **DSD vs. DC split** — what percentage of Walgreens orders are direct store delivery?

**Technical (then these):**
5. **A2000 variant** — which exact version? EDI module active? Which transaction sets configured?
6. **Outlook environment** — Microsoft 365 business? On-prem Exchange? Shared inbox or individual?
7. **Sample POs** — can we get 10 real (redacted) POs for trial calibration?
8. **Daily PO volume** — peak and average? How many unique customers?
9. **Success metric** — what does "this worked" look like to him in 14 days? Hours saved? POs processed? Error rate?
10. **Timeline** — when can we install? Who on his side is our point of contact for the trial?

Bonus if time:
11. **The 50-company network** — which 2 would he open the door to first if trial succeeds?
12. **Apparel SKUs** — size/color matrix POs or flat line items?

---

## Core Value Pitch — "Why You?" (when he asks)

He will ask. Don't rehearse this so stiff it sounds canned. The bones:

> "You said last time you invest in people, not code. Here's who you're investing in: Conaugh McKenna — 22, built OASIS AI from zero, runs a community at $3K MRR with 100% retention, and ships production code every week. Adon — network guy, brings the doors open. We're three to six months early on what's coming in this space, and we're building it as a long-term platform, not a tool to flip. Local-first means you own the infrastructure — if we disappeared tomorrow, Hermes still runs on your machine. And this won't get commoditized in five months because the moat isn't the AI — it's the integration work into A2000, EDI, your specific workflow, Walgreens's compliance rules. That's what OASIS AI does. Five years from now, Hermes is a 30-person team that knows your business better than your own employees."

---

## The 6 Objections He'll Raise

### 1. "This is sci-fi — how do I know it works?"
> "That's exactly why the trial is 14 days and free. You don't pay a dollar until you've watched him process real POs on your real A2000 with your real team looking over his shoulder. Every action is in the audit log. If you don't believe it worked, you show us the log and we fix it or you walk."

### 2. "How do I know you won't disappear in 6 months?"
> "Three answers. One — OASIS AI is our full-time thing, not a side hustle. Two — the model runs on your machine, so if we vanished, Hermes keeps working. You own the code deployment, we export it on request. Three — our Bennett community is 158 members with 100% retention because we don't ghost. We're a long-term partnership operation."

### 3. "What if Hermes makes a mistake on a real order?"
> "Escalation is built in. If Hermes isn't 95%+ confident on any step, he stops and emails a human. Every action is logged — you can rewind anything. And during the trial, he runs in supervised mode — nothing hits A2000 without a human confirming the first 50 orders. By day 14, you've seen every edge case."

### 4. "What does this cost?"
> "Free for 14 days. After that, $1,500/month base plus $0.50 per PO over 1,000 monthly. At your volume that's roughly $1,800/month. One AP hire is $4,000+. Hermes is less than half, 24/7, never quits. If he prevents just a few hundred dollars in Walgreens fines a week, he pays for himself before the invoice lands."

### 5. "I don't want to change how my team works."
> "You won't. Hermes slots into your stack — he reads your Outlook, he writes to your A2000, he sends from your email. Your team keeps doing what they do. The only thing that changes is that 70% of the copy-paste stops happening. They spend their time on the 30% that needs judgment."

### 6. "Wait, you can do the EDI 856 and labels too?"
> "Yes — that's actually the highest-value piece. Anyone can parse a PO. Not many can keep you compliant with Walgreens automatically. The ASN transmission, the GS1-128 labels, the 4-week dispute window tracking — that's Phase 2b. It's in the roadmap. [Open BUILD_PLAN.md Phase 2b.] That's the difference between a system that saves time and a system that saves you fifty to a hundred and fifty thousand dollars a year."

---

## Post-Meeting Follow-Up (within 24 hours)

- [ ] **Summary email** from Conaugh — recap the agenda, the demo, the trial terms, next steps. Tight. 150 words max.
- [ ] **DocuSign trial agreement** sent same day. Don't wait for him to ask.
- [ ] **WhatsApp group chat** created — Conaugh + Adon + Emmanuel. Title: "Hermes × Lowinger." First message from Adon: "In."
- [ ] **Calendar invite** for kickoff call, 3–5 business days out, 30 min. Don't ask him when — propose two times and let him pick.
- [ ] **Internal note** — log the chargeback exposure number, A2000/Outlook answers, EDI VAN status in `project_emmanuel_lowinger.md`, update `memory/SESSION_LOG.md`.
- [ ] **Adon task** — identify the 2 network companies Emmanuel named, pre-research them before the trial ends.

---

## Appendix: Key Lines to Practice

Drop these naturally, don't force them. If they land once, that's enough.

1. **"Hermes is your teammate, not your tool."**
2. **"He runs 24/7. He never sleeps, never forgets, never asks for overtime."**
3. **"Every action is logged. You can audit anything he's ever done."**
4. **"Your data stays on your machine. We don't phone home."**
5. **"When you're at a trade show, Hermes is still shipping orders for you."**
6. **"The ASN going out four hours before the truck — that's the one that keeps Walgreens from fining you automatically. That's what Hermes does while you sleep."**

---

## Final Reminder

Match his intensity. He cut weed and nicotine — he's running hot. Meet him there. Don't be polite-soft. Be direct-warm. He asked to be put ON his plate, not taken off — so every ask we make (sample POs, kickoff date, network intros) is a gift of focus, not a burden.

Walk in knowing we built what we said we'd build. The demo is real. The trial is fair. The pricing is honest. The partnership is long-term.

Only good things from now on.
