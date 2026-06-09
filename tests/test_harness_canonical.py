"""empire-harness LOCKSTEP drift gate (synced via Fleet V2). Every entry point's
LOCKSTEP block must match the vendored canonical (.harness/, pinned in harness.lock).
Edit the canonical in CC90210/empire-harness + re-adopt — never hand-edit a block."""
import re, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / ".harness" / "LOCKSTEP_tool_discipline.md"
BLOCK = re.compile(r"<!-- LOCKSTEP:tool_discipline -->.*?<!-- /LOCKSTEP:tool_discipline -->", re.DOTALL)
ENTRY = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", "ANTIGRAVITY.md", "OPENCODE.md"]
class TestHarnessCanonical(unittest.TestCase):
    def test_entry_points_match_canonical(self):
        canon = BLOCK.search(CANON.read_text(encoding="utf-8")).group(0)
        for name in ENTRY:
            f = ROOT / name
            if not f.exists():
                continue
            m = BLOCK.search(f.read_text(encoding="utf-8"))
            self.assertIsNotNone(m, f"{name} missing LOCKSTEP block")
            self.assertEqual(m.group(0), canon, f"{name} LOCKSTEP drifted from empire-harness canonical")
if __name__ == "__main__":
    unittest.main()
