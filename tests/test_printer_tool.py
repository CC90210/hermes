"""
tests/test_printer_tool.py
--------------------------
Tests for scripts/printer_tool.py

Strategy:
  - All win32print / win32api calls are mocked via unittest.mock so these
    tests run correctly on any platform (including non-Windows CI).
  - We patch _WIN32_AVAILABLE at the module level when testing degradation.
"""
from __future__ import annotations

import json
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Add project root to path so imports work from the tests/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.printer_tool as pt


# ---------------------------------------------------------------------------
# Non-Windows degradation
# ---------------------------------------------------------------------------

class TestNonWindowsDegradation:
    """All operations must return meaningful errors when pywin32 is missing."""

    def test_list_printers_no_win32(self, capsys):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.list_printers()
        assert result == []
        captured = capsys.readouterr()
        assert "pywin32" in captured.err

    def test_default_printer_no_win32(self, capsys):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.default_printer()
        assert result is None
        captured = capsys.readouterr()
        assert "pywin32" in captured.err

    def test_print_pdf_no_win32(self):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.print_pdf("somefile.pdf")
        assert result.success is False
        assert "pywin32" in (result.error or "")

    def test_print_zpl_raw_no_win32(self):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.print_zpl_raw(b"^XA^XZ", "FakePrinter")
        assert result.success is False
        assert "pywin32" in (result.error or "")

    def test_cancel_job_no_win32(self):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.cancel_job(42, "FakePrinter")
        assert result.success is False
        assert "pywin32" in (result.error or "")

    def test_job_status_no_win32(self):
        with patch.object(pt, "_WIN32_AVAILABLE", False):
            result = pt.job_status(42)
        assert "error" in result
        assert "pywin32" in result["error"]


# ---------------------------------------------------------------------------
# list_printers with mocked win32print
# ---------------------------------------------------------------------------

class TestListPrinters:
    def _make_win32print_mock(self, printers: list[dict], default: str = "") -> MagicMock:
        mock = MagicMock()
        mock.EnumPrinters.return_value = printers
        mock.GetDefaultPrinter.return_value = default
        mock.PRINTER_ENUM_LOCAL = 2
        mock.PRINTER_ENUM_CONNECTIONS = 4
        return mock

    def test_returns_printer_info_list(self):
        raw = [
            {"pPrinterName": "HP LaserJet", "pDriverName": "HP PCL6", "pPortName": "USB001", "Status": 0},
            {"pPrinterName": "Zebra ZT411", "pDriverName": "ZPL", "pPortName": "ZBR0001", "Status": 0},
        ]
        mock_win32print = self._make_win32print_mock(raw, default="HP LaserJet")
        with patch.object(pt, "_WIN32_AVAILABLE", True), patch.object(pt, "win32print", mock_win32print, create=True):
            result = pt.list_printers()

        assert len(result) == 2
        assert result[0].name == "HP LaserJet"
        assert result[0].is_default is True
        assert result[1].name == "Zebra ZT411"
        assert result[1].is_default is False

    def test_empty_printer_list(self):
        mock_win32print = self._make_win32print_mock([])
        with patch.object(pt, "_WIN32_AVAILABLE", True), patch.object(pt, "win32print", mock_win32print, create=True):
            result = pt.list_printers()
        assert result == []


# ---------------------------------------------------------------------------
# CLI --list --json
# ---------------------------------------------------------------------------

class TestCLIListJson:
    def test_list_json_output(self, capsys):
        raw = [
            {"pPrinterName": "TestPrinter", "pDriverName": "GenericPCL", "pPortName": "LPT1", "Status": 0},
        ]
        mock_win32print = MagicMock()
        mock_win32print.EnumPrinters.return_value = raw
        mock_win32print.GetDefaultPrinter.return_value = "TestPrinter"
        mock_win32print.PRINTER_ENUM_LOCAL = 2
        mock_win32print.PRINTER_ENUM_CONNECTIONS = 4

        with patch.object(pt, "_WIN32_AVAILABLE", True), \
             patch.object(pt, "win32print", mock_win32print, create=True), \
             patch("sys.argv", ["printer_tool.py", "--list", "--json"]):
            exit_code = pt.main()

        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[0]["name"] == "TestPrinter"
        assert data[0]["is_default"] is True

    def test_list_json_no_win32(self, capsys):
        with patch.object(pt, "_WIN32_AVAILABLE", False), \
             patch("sys.argv", ["printer_tool.py", "--list", "--json"]):
            exit_code = pt.main()

        assert exit_code == 0  # graceful, not an error exit
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "printers" in data or isinstance(data, list)


# ---------------------------------------------------------------------------
# print_zpl_raw — verifies the exact win32print call sequence
# ---------------------------------------------------------------------------

class TestPrintZplRaw:
    def _make_win32print_mock(self) -> MagicMock:
        mock = MagicMock()
        mock.OpenPrinter.return_value = MagicMock()
        mock.StartDocPrinter.return_value = 99  # fake job_id
        return mock

    def test_calls_correct_sequence(self):
        mock_win32print = self._make_win32print_mock()
        zpl = b"^XA^FO50,50^ADN,36,20^FDHello^FS^XZ"

        with patch.object(pt, "_WIN32_AVAILABLE", True), \
             patch.object(pt, "win32print", mock_win32print, create=True):
            result = pt.print_zpl_raw(zpl, "ZebraPrinter")

        assert result.success is True
        assert result.job_id == 99
        assert result.printer_name == "ZebraPrinter"
        assert result.error is None

        # Verify call sequence: Open → StartDoc → StartPage → Write → EndPage → EndDoc → Close
        h = mock_win32print.OpenPrinter.return_value
        mock_win32print.OpenPrinter.assert_called_once_with("ZebraPrinter")
        mock_win32print.StartDocPrinter.assert_called_once_with(h, 1, ("Hermes ZPL", None, "RAW"))
        mock_win32print.StartPagePrinter.assert_called_once_with(h)
        mock_win32print.WritePrinter.assert_called_once_with(h, zpl)
        mock_win32print.EndPagePrinter.assert_called_once_with(h)
        mock_win32print.EndDocPrinter.assert_called_once_with(h)
        mock_win32print.ClosePrinter.assert_called_once_with(h)

    def test_returns_failure_on_exception(self):
        mock_win32print = MagicMock()
        mock_win32print.OpenPrinter.side_effect = OSError("Printer offline")

        with patch.object(pt, "_WIN32_AVAILABLE", True), \
             patch.object(pt, "win32print", mock_win32print, create=True):
            result = pt.print_zpl_raw(b"^XA^XZ", "OfflinePrinter")

        assert result.success is False
        assert "Printer offline" in (result.error or "")


# ---------------------------------------------------------------------------
# PrintResult dataclass JSON serialisation
# ---------------------------------------------------------------------------

class TestPrintResultJson:
    def test_print_result_serialisable(self):
        r = pt.PrintResult(success=True, job_id=7, printer_name="HP", error=None)
        d = asdict(r)
        assert json.dumps(d)  # must not raise
        assert d["success"] is True
        assert d["job_id"] == 7
