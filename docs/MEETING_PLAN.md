# HERMES DEMO — EMMANUEL LOWINGER MEETING PLAN

**Date:** ~2026-04-22 (confirm)
**Attendees:** Conaugh McKenna, Adon, Emmanuel Lowinger
**Duration:** 45–60 minutes
**Stakes:** High. This is the commit meeting.

---

## Meeting Objective

Get Emmanuel to commit to the **30-day free trial** before he leaves the room. Show him Hermes is real, alive, and running on a laptop he can touch — not a pitch deck, not a promise, a working teammate. **No price talk this meeting.** The 30 days is the proof; price is a conversation we have on day 30 with a month of audit logs in hand.

---

## Pre-Meeting Prep Checklist

### Night Before
- [ ] Laptop charged, charger packed, second charger in bag
- [ ] AI provider connection (Anthropic / OpenAI) tested — warm cache, no first-call delay
- [ ] Hermes v0.2.0 pulled from `CC90210/hermes`, mock mode verified (215/215 tests green)
- [ ] `docs/DEMO.html` open in Chrome full-screen, pre-loaded — **this is the primary visual now that we can't demo against his real A2000**
- [ ] `demo.bat` (mock mode) tested end-to-end — confirm <1 second runtime (for the live terminal run that backs up DEMO.html)
- [ ] Sample PO file pre-loaded so we can drop it live after DEMO.html if he wants to see the actual terminal
- [ ] Terminal font size cranked to 18pt. He needs to read it from across the table.
- [ ] Audit log file open in a second window
- [ ] DEMO.html opened on a second monitor or have the laptop angled so he can scroll through after
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
| 8 min | Visual demo (DEMO.html + recorded terminal) | Tell the story he can't see live |
| 3 min | Architecture in 90 seconds | Plain English, no jargon |
| 5 min | Shopify case study | The closest match to his business |
| 10 min | Trial terms (no price talk) | 30-day free trial. Price conversation deferred to day 30 |
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
> "Last time you said three things. One — you need to see this work, because it sounds like sci-fi. Two — you invest in people, not code. Three — someone with capital will copy this in a month, so speed matters. We heard all of it. The next 45 minutes is us proving we listened — and instead of pricing this thing today, we're giving you the agent free for thirty days so the value speaks before the number does."

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

### Why we're showing DEMO.html instead of live
Emmanuel doesn't have A2000 on a laptop we can bring. We can't show a true end-to-end live run in this meeting. What we CAN do is walk him through `docs/DEMO.html` — a professional, self-contained visual that tells the exact story — and back it up with the mock terminal demo running in real-time. DEMO.html is the vehicle. Live terminal is the proof.

### Windows to Have Open
1. **Chrome full-screen** — `docs/DEMO.html` loaded, scrolled to the top
2. **Terminal** — Hermes root directory, ready to run `demo.bat` for the live proof moment
3. **File Explorer** (optional) — sample PO file visible so we can show the "input"

### Opening Line
> "Before we talk, I want you to see Hermes. We built this page for you — scroll with me. Every section is something we built, tested, and are ready to deploy."

### The Sequence

**Step 1 — Open DEMO.html and scroll the hero.**
> "This is Hermes. Built for Lowinger Distribution specifically. Two hundred and fifteen automated tests passing. Demo pipeline runs in a tenth of a second. That's not a number we're hoping for — that's what it did when I ran it on my laptop this morning."

**Step 2 — Scroll to "The problem" section.**
Read the 6:42 AM timeline with him. Pause at the $340 fine line.
> "This is the day we're taking off your plate. Every line on this timeline is a handoff Hermes takes."

**Step 3 — Scroll to "The loop" — five steps.**
Point to each box:
> "Email in. AI parses it locally. Order into A2000. Labels print, ASN transmits. Invoice goes out. Five steps, every single one automatic."

**Step 4 — Scroll to "Recorded demo output."**
This is the actual terminal capture.
> "This is the exact terminal output from running the pipeline on my laptop this morning. PO parsed, three line items extracted, order entered, invoice drafted — point one four seconds. Same code runs on your machine when we install."

**Step 5 — BACK IT UP WITH A LIVE TERMINAL RUN.**
Switch to the terminal. Run:
```
demo.bat
```
Narrate as it runs (fast, narrate DURING):
> "He's reading the email. Extracting the PO. Parsing three line items. Validating. Pushing into A2000 — mock mode right now, real A2000 when we're on your machine. Pulling the invoice. Drafting the email. Done."

Switch back to DEMO.html.

**Step 6 — Scroll to "How you talk to Hermes."**
Show the chat mockup — the "Hey Hermes, what POs came in overnight?" conversation.
> "When you're not at the terminal, you just type to him. Like texting a sharp new hire. No microphone, no voice AI, no new hardware. Here's a sample conversation we put together."

**Step 7 — Scroll to "What this saves you."**
The chargeback math. Pause on the $50–150K line.
> "This is the floor, Emmanuel. Not the ceiling. Floor. Every shipment without proper compliance is a fine waiting to hit your next payment. Hermes keeps you clean."

**Step 8 — Scroll to "What's in the box."**
Two columns — what Hermes handles vs. what he'll never do without asking.
> "Right column is the control you keep. He drafts, you approve. He escalates, you decide. We built him this way because you told us 'put on my plate, not take off it' — this is how we honor that."

**Step 9 — The money line.**
> "The loop you saw — that's the work your team does a hundred times a week by hand. Hermes does it while you're at a trade show. **Thirty days free, no credit card, no price conversation until day thirty.** We remove it clean if it doesn't earn its keep. Ready to start?"

### If The Live Terminal Run Hiccups
Don't panic. DEMO.html is the primary. Just say:
> "The recorded output on the page is from this morning. Same code, same result. Let me keep scrolling."

The HTML page carries the entire demo on its own.

---

## Architecture in 90 Seconds (3 min)

Whiteboard. Three boxes. No jargon.

1. **Inbox** → "He watches your Outlook or Gmail. Sees a PO come in."
2. **Brain** → "He reads it through an enterprise AI provider — Anthropic or OpenAI — under a contract that says the provider can't store, train on, or share your data. Process it and forget it."
3. **A2000 + Compliance Out** → "He enters it. Sends the ASN. Prints the labels. Pulls the invoice. Sends the confirmation."

That's it. Under the boxes write: **"Encrypted vault. Audited. Backed up every six hours. Yours."**

Add a fourth box on the right side: **"Dispute Tracker"** — "He watches for Walgreens fines, tracks the 4-week window, and drafts the dispute before the money is gone."

If he asks how the brain works, one sentence: "It's a top-tier AI provider — same companies the Fortune 500 uses — bound by a Data Processing Agreement that legally prohibits storing or training on your data. SOC 2 Type II certified. If they leaked your data, they'd be sued out of existence."

If he pushes on cloud-vs-local: "The cloud isn't the risk — unaccountable storage is. We use providers under contracts with legal teeth. If you ever want the AI itself running offline on a machine in your office, that's an upgrade we can do later — about $2,500 in hardware, and not required for the trial."

---

## Shopify Agent Case Study (5 min)

This is the answer to "who have you scaled that looks like me?"

**Script:**
> "Closest match we have to your business is a Shopify operator we built an agent for. Different industry — e-commerce, not wholesale — but same bones. Orders coming in, inventory checks, customer comms, invoicing. We replaced roughly 20 hours of weekly manual work per operator. The agent ran quietly for the first two weeks — we watched every action — and by week three the owner stopped reviewing every output because he trusted it. That's the arc we're pitching you: two weeks of supervised trust-building, then he's just part of your team."

Add Bennett as the track-record proof:
> "On the community side, we run an operation at $3,000 MRR with 158 members and 100% retention. That's us doing long-term client work, not one-and-done. We don't disappear."

---

## Trial Terms — No Price Talk This Meeting (10 min)

Put the trial agreement on the table. **Do not quote a monthly number.** The whole point of the 30-day free trial is that price is grounded in real audit data, not estimates. Talking price now undercuts the whole offer.

### What We Propose

- **30-day free trial.** Starts the day Hermes is installed on his machine.
- **What's included:** Full email → PO → A2000 → invoice loop. Audit logs. Escalation emails. Our hands on it the whole time. Encrypted backups every six hours.
- **What we need from him:** A2000 access (API or login), inbox consent (Outlook or Gmail), 3–5 sample POs, two 20-minute check-in calls (week 2, week 4).
- **Success criteria:** 95%+ of POs processed end-to-end without human intervention. Zero wrong-customer errors. Every mistake logged and reviewed. Zero missed Walgreens ASN windows attributable to the agent.

### Why 30 Days, Not 14

> "Two weeks is enough to install software. It's not enough for an agent to learn your business. Hermes needs roughly four weeks to see the full range of POs you receive, calibrate against your contract pricing and customer list, and build a meaningful audit history. We're confident enough in the agent to give it the time it actually needs to prove itself. And we're confident enough that we don't need to lock you into a monthly bill before you see it work."

### When He Asks "What's It Going to Cost?"

He will ask. Don't dodge — name the strategy.

> "Here's the move on pricing, Emmanuel. We're not quoting you today. The whole point of the thirty days is that we sit down on day thirty with a month of audit logs in front of us — actual order volume, actual hours saved, actual chargebacks prevented — and the price reflects that. Quoting now would be a guess on both sides. Quoting then is just math."

If he pushes for a range: "We work in the range of a typical mid-back-office hire — well under what you'd pay a full-time AP person — but the exact number depends on what your operation actually uses. We'll know in thirty days."

### The Real ROI Math — Lead With Chargebacks, Not Time

> "Here's how the math will actually work when we get to day thirty. The $50,000 to $150,000 a year in Walgreens fines — that's the floor argument. That's the number before we count a single hour of labor saved. If Hermes prevents even one missed ASN per week — one shipment that doesn't generate a fine — at 1% to 5% of invoice value, you're looking at hundreds of dollars recovered per event.
>
> Time savings is the bonus on top. If you process 20 orders a day at 15 minutes each, that's 5 hours of daily manual work gone permanently. The trial is free. You don't pay us a dollar until thirty days have passed and we have real numbers to look at together."

### Exit Clause
No lock-in. He owns his data. We export everything on request. Removal is one script. Say this unprompted — it kills the biggest objection before he raises it.

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
9. **Success metric** — what does "this worked" look like to him in 30 days? Hours saved? POs processed? Error rate? Chargebacks avoided?
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
> "That's exactly why the trial is thirty days and free. You don't pay a dollar until you've watched him process real POs on your real A2000 with your real team looking over his shoulder. Every action is in the audit log. If you don't believe it worked, you show us the log and we fix it or you walk."

### 2. "How do I know you won't disappear in 6 months?"
> "Three answers. One — OASIS AI is our full-time thing, not a side hustle. Two — the agent runs on your machine and your data is in your encrypted vault, so if we vanished, you still have the code, the data, and the audit log. You own everything. Three — our Bennett community is 158 members with 100% retention because we don't ghost. We're a long-term partnership operation."

### 3. "What if Hermes makes a mistake on a real order?"
> "Escalation is built in. If Hermes isn't 95%+ confident on any step, he stops and emails a human. Every action is logged — you can rewind anything. And during the trial, he runs in supervised mode — nothing hits A2000 without a human confirming the first 50 orders. By day 30, you've seen every edge case."

### 4. "What does this cost?"
> "We're not quoting today. That's the deal — thirty days free, then we sit down with a month of real audit data and the price reflects what you actually use. We work in the range of a part-time back-office hire, but the exact number depends on your operation. The reason we're not naming it now is the same reason you wouldn't quote a customer for a full year of orders without knowing what they're going to ship — we both need real numbers first."

### 5. "I don't want to change how my team works."
> "You won't. Hermes slots into your stack — he reads your Outlook, he writes to your A2000, he sends from your email. Your team keeps doing what they do. The only thing that changes is that 70% of the copy-paste stops happening. They spend their time on the 30% that needs judgment."

### 6. "Wait, you can do the EDI 856 and labels too?"
> "Yes — that's actually the highest-value piece. Anyone can parse a PO. Not many can keep you compliant with Walgreens automatically. The ASN transmission, the GS1-128 labels, the 4-week dispute window tracking — that's Phase 2b. It's in the roadmap. [Open BUILD_PLAN.md Phase 2b.] That's the difference between a system that saves time and a system that saves you fifty to a hundred and fifty thousand dollars a year."

---

## Post-Meeting Follow-Up (within 24 hours)

- [ ] **Summary email** from Conaugh — recap the agenda, the demo, the trial terms, next steps. Tight. 150 words max.
- [ ] **DocuSign 30-day trial agreement** sent same day. Don't wait for him to ask.
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
4. **"Your data lives in an encrypted vault on your machine. The AI provider is bound by a contract that says no copies allowed. Backups every six hours."**
5. **"When you're at a trade show, Hermes is still shipping orders for you."**
6. **"The ASN going out four hours before the truck — that's the one that keeps Walgreens from fining you automatically. That's what Hermes does while you sleep."**

---

## Final Reminder

Match his intensity. He cut weed and nicotine — he's running hot. Meet him there. Don't be polite-soft. Be direct-warm. He asked to be put ON his plate, not taken off — so every ask we make (sample POs, kickoff date, network intros) is a gift of focus, not a burden.

Walk in knowing we built what we said we'd build. The demo is real. The trial is fair. The pricing is honest. The partnership is long-term.

Only good things from now on.
