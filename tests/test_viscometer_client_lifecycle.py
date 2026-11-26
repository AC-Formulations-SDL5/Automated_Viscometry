"""Unit tests for ViscometerClient reconnect / ensure_alive lifecycle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from viscometry.hardware.viscometer.client import (
    ViscometerClient,
    _looks_like_serial_fault,
)


def _client_without_subprocess() -> ViscometerClient:
    with patch.object(ViscometerClient, "__init__", lambda self, *a, **k: None):
        client = ViscometerClient.__new__(ViscometerClient)
    client._conn = {
        "port": "COM6",
        "baud": 115200,
        "timeout": 1.0,
        "spindle_k": 992.47,
    }
    client._last_ok_ts = 0.0
    client.proc = MagicMock()
    client.q = MagicMock()
    return client


def test_looks_like_serial_fault_detects_writefile():
    exc = RuntimeError(
        "zero failed: WriteFile failed (PermissionError(13, "
        "'The device does not recognize the command.', None, 22))"
    )
    assert _looks_like_serial_fault(exc) is True
    assert _looks_like_serial_fault(RuntimeError("no valid packet")) is False


def test_ensure_alive_ping_ok_no_reconnect():
    client = _client_without_subprocess()
    client._last_ok_ts = 1e12  # recent
    client.ping = MagicMock(return_value={"cleaned": "OK"})
    client.reconnect = MagicMock()

    data = client.ensure_alive(reason="cell start", idle_reconnect_s=45.0)

    assert data["cleaned"] == "OK"
    client.reconnect.assert_not_called()
    client.ping.assert_called_once()


def test_ensure_alive_proactive_reconnect_after_idle():
    client = _client_without_subprocess()
    client._last_ok_ts = 0.0  # very old → idle
    client.reconnect = MagicMock(return_value={"reconnected": True})
    client.ping = MagicMock(return_value={"cleaned": "OK"})

    client.ensure_alive(reason="after lid", idle_reconnect_s=15.0)

    client.reconnect.assert_called()
    client.ping.assert_called_once()


def test_ensure_alive_recovers_after_ping_serial_fault():
    client = _client_without_subprocess()
    client._last_ok_ts = 1e12
    serial_err = RuntimeError("WriteFile failed (PermissionError(13))")
    client.ping = MagicMock(side_effect=[serial_err, {"cleaned": "OK"}])
    client.reconnect = MagicMock(return_value={"reconnected": True})

    data = client.ensure_alive(reason="retry", idle_reconnect_s=None, max_attempts=2)

    assert data["cleaned"] == "OK"
    assert client.reconnect.call_count == 1
    assert client.ping.call_count == 2


def test_safe_stop_soft_swallows_persistent_failure():
    client = _client_without_subprocess()
    client.stop = MagicMock(
        side_effect=RuntimeError("WriteFile failed (PermissionError(13))")
    )
    client.reconnect = MagicMock(return_value={})

    result = client.safe_stop(reason="pre-measure", soft=True)

    assert result is None
    assert client.stop.call_count == 2
    client.reconnect.assert_called_once()


def test_safe_zero_retries_then_succeeds():
    client = _client_without_subprocess()
    client.zero = MagicMock(
        side_effect=[
            RuntimeError("WriteFile failed (PermissionError(13))"),
            {"raw": "Z"},
        ]
    )
    client.reconnect = MagicMock(return_value={})

    result = client.safe_zero(reason="cell 11", soft=True)

    assert result == {"raw": "Z"}
    assert client.zero.call_count == 2


def test_reconnect_requires_prior_init():
    client = _client_without_subprocess()
    client._conn = None
    with pytest.raises(RuntimeError, match="not initialized"):
        client.reconnect()
