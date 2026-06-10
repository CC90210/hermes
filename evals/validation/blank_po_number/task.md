# Validation scenario for adapters.po_parser.validate_po (the real pre-order-entry gate).
# A whitespace-only PO number must be treated as missing (mirrors the repo's own
# test_validate_po_blank_po_number unit test) — not silently accepted.
blank_po_number
