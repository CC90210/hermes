---
tags: [hermes, skill]
---

# SKILL — PO Parsing

> How Hermes reads and extracts structured data from purchase orders.

## When to Trigger

The parser runs in Stage 2 of the pipeline: after `EmailAgent.poll_inbox()` returns
a raw email dict. `POParser.parse_and_persist()` is the entry point. The functional
`parse_po()` function is available for testing individual files directly.

## The Process

```
raw email dict
    ↓
1. Detect format          (filename extension + content_type)
    ↓
2. Extract text           (format-specific extractor)
    ↓
3. Send to Ollama          (local LLM, temperature=0, format=json)
    ↓
4. Validate extracted data (validate_po() — returns errors list)
    ↓
5. Persist to DB           (create_order + create_order_line rows)
    ↓
returns order_id (int)
```

## Format Detection

Detection is based on filename extension first, content_type second. Precedence:

| Priority | Condition | Extractor |
|----------|-----------|-----------|
| 1 | `.pdf` or `application/pdf` | `_extract_text_pdf()` — pdfplumber, all pages |
| 2 | `.xlsx`, `.xls`, `spreadsheet`, `excel` | `_extract_text_excel()` — openpyxl, all sheets |
| 3 | `.edi`, `.x12`, `.850`, `edi` | `_extract_text_edi()` — custom X12 segment parser |
| 4 | `.html`, `.htm`, `html` | `_extract_text_html()` — regex tag stripper |
| 5 | anything else | plain text decode (UTF-8 with error replacement) |

When processing an email with attachments, the **first** PO-looking attachment is parsed.
If no attachment matches, the email body is parsed as plain text.

## LLM Prompt Strategy

The extraction prompt (`_EXTRACTION_PROMPT`) is injected with up to 12,000 characters
of extracted text. Key design decisions:

- `format: "json"` in the Ollama payload — forces valid JSON output (no markdown fences)
- `temperature: 0.0` — deterministic, no hallucination risk
- Explicit null instructions for every field — LLM must output `null` not an empty string
- UPC field extraction — useful for A2000 SKU matching in apparel/wholesale
- Rules section in the prompt disambiguates common patterns (e.g. "EA", "CS", "EACH")

The model defaults to `qwen2.5:32b` (`OLLAMA_MODEL` env var). This model is strong at
structured extraction and runs locally on 24GB+ VRAM. Smaller deployments can use
`qwen2.5:7b` with some accuracy reduction.

## Common Edge Cases

**Missing PO number:**
- LLM returns `null` for `po_number`
- `validate_po()` catches this — returns "Missing PO number."
- Order is persisted as `FAILED` and escalation is triggered
- Do NOT invent a PO number from the email subject line

**Ambiguous line items:**
- If `quantity <= 0`, `validate_po()` flags it
- If `description` is empty, `validate_po()` flags it
- Items with `unit_price = 0.0` are allowed (not all POs include pricing)

**EDI with non-standard separators:**
- The EDI parser reads element separator from position [3] of the ISA segment
- Segment separator is read from position [105] of the ISA envelope
- If the file is malformed (no ISA), parsing falls back to raw text decode
- Non-standard qualifiers in PO1 (e.g. `BP`, `VN`, `IN` for SKU) are handled
  by the qualifier map in `_extract_text_edi()`

**Multi-page PDFs:**
- pdfplumber extracts all pages and joins with `\n`
- Text is truncated at 12,000 chars before sending to Ollama
- For very long POs, line items near the end may be cut off — this is a known
  limitation; increase the truncation limit if the client sends large POs

## Failure Escalation

If parsing fails (exception in `parse_and_persist`):
1. Exception propagates to `Orchestrator.run_cycle()`
2. Orchestrator logs the failure and increments `failed` counter
3. No order row is created (the exception aborts before `create_order`)
4. On next `handle_failures()` call, the Orchestrator escalates if threshold is met

If parsing succeeds but validation fails:
1. Order row is created with status `PARSED`
2. `POSAgent.enter_order()` catches the validation error and sets status `FAILED`
3. Escalation is sent with the specific validation errors listed

## Obsidian Links
- [[brain/CAPABILITIES]] | [[brain/ARCHITECTURE]] | [[skills/a2000-integration/SKILL]]
