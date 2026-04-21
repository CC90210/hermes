# Hermes — Setup Guide
**Your Plain-English Guide to the System**
**Prepared by OASIS AI Solutions**

---

## What This System Does

Hermes reads your incoming purchase order emails, enters each order into A2000 automatically, retrieves the invoice A2000 generates, and emails it back to your buyer — without you touching the keyboard. It runs in the background on your computer, processing orders as they arrive. You only get a notification when something genuinely needs your attention.

---

## What You Need

### Hardware
- A Windows computer with **16 GB RAM or more** (the computer you run A2000 on works fine)
- A stable internet connection (for reading your Outlook inbox)
- The computer needs to be **on and running** during business hours for the system to process orders

### Software
Everything else is installed by OASIS AI during the setup call. You do not need to install anything yourself. We handle:
- Ollama (the local AI that reads your POs)
- Python (the engine that runs the agents)
- All required libraries and dependencies

### Credentials You Provide Once
- Your Outlook email credentials or Microsoft 365 sign-in
- Your A2000 login (admin account or API credentials)

These are stored securely on your machine. You provide them once during setup and never again.

---

## How It Works

```
Step 1: A PO email arrives in your Outlook inbox from Walgreens (or any buyer)

Step 2: The Email Agent reads the email and attachment every 5 minutes
        It identifies it as a PO and extracts all the line items

Step 3: The POS Agent opens A2000 and enters the order
        Every SKU, quantity, and shipping date — exactly as it appears on the PO

Step 4: A2000 generates an invoice (same as it always does)

Step 5: The Invoice Agent retrieves that invoice
        and emails it back to the buyer from your Outlook account

Step 6: You receive a summary:
        "PO #WG-88291 processed. 12 items entered. Invoice sent. 4 minutes total."
```

For routine orders, you are not involved at all. For anything unusual (a new buyer format, an item that is out of stock, a PO that looks wrong), the system pauses and asks for your input.

---

## How to Start It

**Option A — Double-click (easiest)**
Find the file called `start.bat` on your Desktop or in the AOS folder. Double-click it. A terminal window will open and you will see:

```
Hermes starting...
Email Agent:    CONNECTED (inbox monitoring active)
A2000 Adapter:  CONNECTED
Manager Bot:    RUNNING
System ready. Processing orders.
```

**Option B — Command line**
Open a terminal (search "Command Prompt" or "PowerShell" in Windows), navigate to the AOS folder, and run:

```
python main.py
```

You will see the same startup messages.

**Leave the window open.** The system runs as long as that window is open. You can minimise it — you do not need to look at it.

---

## How to Stop It

Click on the terminal window and press **Ctrl + C** (hold the Control key and press C).

The system will finish any order it is currently processing and then shut down cleanly. You will see:

```
Shutting down gracefully...
Manager Bot stopped.
All agents stopped.
Hermes offline.
```

It is safe to close the window after this message appears.

---

## How to Check System Status

Open a new terminal, navigate to the AOS folder, and run:

```
python main.py --health
```

You will see a status report like this:

```
HERMES — HEALTH CHECK
──────────────────────────────
Email Agent:       RUNNING  (last check: 2 min ago)
A2000 Adapter:     CONNECTED
Invoice Agent:     RUNNING
Manager Bot:       RUNNING

Orders Today:      14 processed, 0 errors
Last Order:        PO #WG-88291 at 9:47 AM — completed in 3 min
Queue:             0 orders pending

System:            HEALTHY
```

---

## Reading the Daily Summary

Every morning, you will receive an email summary from the system. It looks like this:

```
Subject: Hermes — Daily Summary (Apr 16)

Yesterday's Activity:
  Orders processed:    8
  Total items entered: 94
  Errors:              0
  Avg. turnaround:     4.2 minutes per order

Alerts requiring your attention: None

Your estimated time saved: 2 hours
```

If there are no alerts, you do not need to do anything. The system handled everything.

---

## What to Do If Something Goes Wrong

**If an order failed:**
You will receive an alert email with:
- Which PO failed (buyer, PO number)
- What went wrong (plain English explanation)
- What to do (usually: enter this one manually, then reply to the alert to let us know)

For failed orders, you can always enter them manually in A2000 as you normally would. The system does not block you from doing anything by hand.

**If the system stops running:**
Restart it by double-clicking `start.bat` again. Most issues resolve themselves on restart.

**If restarting does not fix it:**
Check the `logs/` folder in the AOS directory. The most recent log file will describe what happened. Forward that file to conaugh@oasisai.work and we will diagnose it, usually within a few hours.

**Emergency contact:**
Email conaugh@oasisai.work or call the number on file. For critical issues (system down during high-volume periods), we respond within 2 hours during business hours.

---

## Frequently Asked Questions

**"Is my data safe?"**
Yes. All your PO data, order history, and customer information is stored encrypted on your own computer. Nothing is sent to any cloud service for processing. The AI that reads your POs (Ollama) runs locally — it never connects to OpenAI or any external AI service. Your Walgreens purchase orders never leave your machine.

**"What if it makes a mistake?"**
The system is designed to escalate rather than guess. If it is not confident about a line item, a price, or a SKU, it flags the order for your review rather than entering potentially wrong data. For orders it does enter, it logs every field it wrote, so you can audit any order instantly. The error rate target is under 5% — meaning 19 out of 20 orders process correctly with zero manual intervention. For that 1 in 20, you handle it normally and let us know so we can tune the parser.

**"Can I still enter orders manually?"**
Absolutely. The system does not change A2000 at all — it just provides an additional way to get orders in. You can enter orders manually whenever you want. If the system and you both try to enter the same order, the system will detect the duplicate and skip it.

**"What if my internet goes down?"**
The system cannot read new emails without internet, but A2000 and all your stored order data remain fully accessible. When internet is restored, the system will check the inbox for any POs that arrived while offline and process them in order. Nothing is lost.

**"What if A2000 is closed or being updated?"**
The system detects when A2000 is not reachable and pauses processing. Orders queue up and are processed automatically once A2000 is back online. You will receive an alert if A2000 has been unreachable for more than 30 minutes.

**"Who can see my system?"**
Only you. OASIS AI cannot access your system unless you contact us for support and explicitly grant remote access for that session. There is no standing remote connection.

---

*Hermes is built and maintained by OASIS AI Solutions.*
*conaugh@oasisai.work | oasisai.work*
