"""Unit tests for Testing-tab viscometer health probe."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from viscometry.hardware.viscometer import health as health_mod


def test_probe_viscometer_success(tmp_path: Path):
    worker = tmp_path / "worker32.py"
    worker.write_text("# stub\n", encoding="utf-8")
    fake_client = MagicMock()
    fake_client.init.return_value = {
        "proto": "1.0",
        "identify_raw": "I....",
        "port": "COM6",
        "baud": 115200,
    }
    fake_client.identify.return_value = {"raw": "I....", "cleaned": "IDENT"}

    with patch.object(health_mod, "ViscometerClient", return_value=fake_client), patch.object(
        health_mod, "WORKER32_DIR", tmp_path
    ):
        result = health_mod.probe_viscometer()

    assert result["ok"] is True
    assert result["state"] == "ok"
    assert result["port"]
    fake_client.init.assert_called_once()
    fake_client.identify.assert_called_once()
    fake_client.close.assert_called_once()


def test_probe_viscometer_init_failure_still_closes(tmp_path: Path):
    worker = tmp_path / "worker32.py"
    worker.write_text("# stub\n", encoding="utf-8")
    fake_client = MagicMock()
    fake_client.init.side_effect = RuntimeError(
        "WriteFile failed (PermissionError(13, 'The device does not recognize the command.', None, 22))"
    )

    with patch.object(health_mod, "ViscometerClient", return_value=fake_client), patch.object(
        health_mod, "WORKER32_DIR", tmp_path
    ):
        result = health_mod.probe_viscometer()

    assert result["ok"] is False
    assert result["state"] == "error"
    assert "WriteFile" in str(result.get("error") or "")
    fake_client.close.assert_called_once()


def test_probe_missing_worker(tmp_path: Path):
    with patch.object(health_mod, "WORKER32_DIR", tmp_path):
        result = health_mod.probe_viscometer()

    assert result["ok"] is False
    assert "not found" in result["message"].lower()
