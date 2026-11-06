"""Structured experiment-duration prediction and append-only training store."""

from __future__ import annotations

from viscometry.timing.model import (
    default_posterior,
    estimate_discovery_probe_phase_s,
    load_posterior,
    predict_cell_seconds,
    predict_run_seconds,
    save_posterior,
    update_posterior_from_rows,
)
from viscometry.timing.training_store import append_rows, ensure_headers

__all__ = [
    "append_rows",
    "default_posterior",
    "ensure_headers",
    "estimate_discovery_probe_phase_s",
    "load_posterior",
    "predict_cell_seconds",
    "predict_run_seconds",
    "save_posterior",
    "update_posterior_from_rows",
]
