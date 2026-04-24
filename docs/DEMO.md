---
mutability: SEMI-MUTABLE
tags: [hermes, demo, client-facing]
---

# Hermes — Demo Package

> Everything needed to show Hermes to a client when we can't run a true live demo against their infrastructure.

## Two deliverables

1. **[`DEMO.html`](DEMO.html)** — the primary visual. Self-contained one-page site. Open in any browser, full-screen, on the laptop in front of Emmanuel. Dark-themed, professional, tells the full story from problem → solution → math → trust → CTA. Works offline. Prints clean to PDF if we need a leave-behind.

2. **The mock terminal run** — `demo\demo.bat` on Windows (or `python -m demo.run_demo`). Backs up DEMO.html with an in-person live pipeline execution. Completes in ~0.1 seconds. Use this AFTER walking through DEMO.html to prove the code is real.

## How to show it

1. Laptop full-screen: `docs/DEMO.html` in Chrome
2. Scroll top-to-bottom with Emmanuel — narrate each section (full script in [`MEETING_PLAN.md`](MEETING_PLAN.md))
3. At the "Recorded demo output" section, switch to a terminal and run `demo.bat` live — mirrors the recorded output
4. Return to the HTML, keep scrolling through value math → trust → path forward

Total walkthrough: ~8 minutes if he doesn't interrupt, ~15 if he asks questions (good sign).

## Architecture diagram (Mermaid)

For markdown viewers (GitHub, Obsidian, Cursor) that render Mermaid natively.

```mermaid
flowchart TD
    Inbox["📧 Your Outlook Inbox"] --> EmailAgent
    Drop["📁 Watched folder<br/>(IMAP-blocked fallback)"] --> EmailAgent

    EmailAgent["Email Agent<br/>poll every 5 min"] --> Parser
    Parser["PO Parser<br/>Ollama local LLM"] --> Manager

    Manager["🧠 Manager Bot<br/>orchestrate · retry · escalate · audit"]

    Manager --> POS["POS Adapter<br/>A2000 4-mode ladder"]
    Manager --> Ack["EDI 855<br/>PO Ack (24-48hr)"]
    Manager --> Labels["GS1-128 Labels<br/>→ Zebra thermal printer"]
    Manager --> ASN["EDI 856 ASN<br/>→ 4hr pre-DC window"]

    POS --> InvoiceGen["Invoice retrieval<br/>from A2000"]
    InvoiceGen --> InvoiceSend["Invoice Agent<br/>SMTP → customer"]

    Remit["EDI 820 Remittance<br/>parsing + deduction detect"] --> Chargeback["Chargeback Tracker<br/>4-week dispute window"]
    Chargeback --> Alert["Desktop notification<br/>+ drafted dispute email"]

    Audit[("🗂 SQLite + Audit Log<br/>encrypted, local, replayable")]

    EmailAgent -.log.-> Audit
    Parser -.log.-> Audit
    Manager -.log.-> Audit
    POS -.log.-> Audit
    Ack -.log.-> Audit
    Labels -.log.-> Audit
    ASN -.log.-> Audit
    InvoiceSend -.log.-> Audit
    Remit -.log.-> Audit
    Chargeback -.log.-> Audit

    IDE["💬 Claude Code<br/>(IDE Hermes — Emmanuel types)"] <-.reads/writes.-> Audit

    classDef primary fill:#c4a572,color:#0a0a0b,stroke:#c4a572
    classDef log fill:#1c1c21,color:#e8e8ea,stroke:#2a2a30
    classDef ext fill:#141417,color:#8a8a92,stroke:#2a2a30

    class Manager primary
    class Audit log
    class Inbox,Drop,IDE ext
```

## The 5-step pipeline (simplified flow)

```mermaid
flowchart LR
    A[📧 PO<br/>received] --> B[🤖 Parsed<br/>locally]
    B --> C[📦 Entered<br/>into A2000]
    C --> D[🏷️ Labels +<br/>ASN sent]
    D --> E[🧾 Invoice<br/>emailed back]

    style A fill:#1c1c21,color:#e8e8ea,stroke:#c4a572
    style B fill:#1c1c21,color:#e8e8ea,stroke:#c4a572
    style C fill:#1c1c21,color:#e8e8ea,stroke:#c4a572
    style D fill:#1c1c21,color:#e8e8ea,stroke:#c4a572
    style E fill:#1c1c21,color:#e8e8ea,stroke:#c4a572
```

## Two-layer deployment

```mermaid
flowchart TB
    subgraph Machine["🖥 Emmanuel's Windows Machine"]
        subgraph Pipeline["Background Hermes<br/>(Task Scheduler, every 5 min)"]
            BG1[Watch inbox]
            BG2[Parse POs]
            BG3[Enter A2000]
            BG4[Send invoices]
            BG5[Generate labels]
        end

        subgraph IDE["IDE Hermes<br/>(Claude Code, interactive)"]
            I1[Answer questions]
            I2[Draft emails]
            I3[Run reports]
            I4[Re-run failed orders]
            I5[Draft disputes]
        end

        DB[("🗂 Shared SQLite DB<br/>+ audit log + memory/")]

        Pipeline <-.reads/writes.-> DB
        IDE <-.reads/writes.-> DB
    end

    classDef layer fill:#1c1c21,color:#e8e8ea,stroke:#2a2a30
    classDef db fill:#c4a572,color:#0a0a0b,stroke:#c4a572

    class Pipeline,IDE layer
    class DB db
```

## Demo narration script (cheat card)

See the full meeting plan at [`MEETING_PLAN.md`](MEETING_PLAN.md) — this is the condensed version to hold in hand during the walkthrough.

| Section in DEMO.html | 30-second line |
|---|---|
| **Hero** | "Built for Lowinger Distribution specifically. 215 tests passing. Pipeline runs in a tenth of a second." |
| **The problem (6:42 AM timeline)** | "This is the day we're taking off your plate. Every line here is a handoff Hermes takes." |
| **The loop (5 steps)** | "Email in. AI parses locally. Order into A2000. Labels print, ASN goes out. Invoice back. All automatic." |
| **Recorded demo output** | "This is the exact terminal output from this morning. PO parsed, invoice drafted — 0.14 seconds." |
| **How you talk to him** | "You type. Like texting a sharp new hire. No microphone, no new hardware." |
| **Value math** | "$50–150K in chargebacks — that's the floor, not the ceiling. Time savings is bonus." |
| **What's in the box** | "Right column is the control you keep. He drafts, you approve. Put on your plate, not take off it." |
| **CTA** | "14 days free, no credit card, removed clean if it doesn't earn its keep." |

## File pointers

- [`DEMO.html`](DEMO.html) — the visual package
- [`MEETING_PLAN.md`](MEETING_PLAN.md) — full meeting script + agenda + objection handling
- [`BUILD_PLAN.md`](BUILD_PLAN.md) — phase-by-phase roadmap (show if he asks "how soon can this go live")
- [`DISCOVERY_QUESTIONS.md`](DISCOVERY_QUESTIONS.md) — the 38 questions to send after the meeting
- [`WHOLESALE_RESEARCH.md`](WHOLESALE_RESEARCH.md) — backup citations for the chargeback math if pushed
