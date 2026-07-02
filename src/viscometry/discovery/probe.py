"""Hardware probe adapter for Discovery Mode (injected callables, no main-loop import)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

from viscometry.discovery.types import ProbeExecutor

RowResolver = Callable[[int], Tuple[int, int]]
MoveFn = Callable[..., Tuple[float, float, float]]
MeasureFn = Callable[..., Optional[List[Dict[str, Any]]]]


def mean_torque_from_measurements(measurements: Optional[List[dict]]) -> Optional[float]:
    """Average torque_percent from measure_torque_at_rpm output."""
    if not measurements:
        return None
    values = []
    for row in measurements:
        try:
            t = row.get("torque_percent")
            if t is not None:
                values.append(float(t))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return sum(values) / len(values)


@contextmanager
def scoped_measurement_duration(
    measure_module: Any,
    *,
    duration_s: float,
    sample_interval_s: Optional[float] = None,
):
    """Temporarily override MEASUREMENT_DURATION on the orchestrator module."""
    old_duration = getattr(measure_module, "MEASUREMENT_DURATION", None)
    old_interval = getattr(measure_module, "SAMPLE_INTERVAL", None)
    try:
        if old_duration is not None:
            measure_module.MEASUREMENT_DURATION = float(duration_s)
        if sample_interval_s is not None and old_interval is not None:
            measure_module.SAMPLE_INTERVAL = float(sample_interval_s)
        yield
    finally:
        if old_duration is not None:
            measure_module.MEASUREMENT_DURATION = old_duration
        if sample_interval_s is not None and old_interval is not None:
            measure_module.SAMPLE_INTERVAL = old_interval


def make_probe_executor(
    cnc: Any,
    client: Any,
    *,
    measure_torque_fn: MeasureFn,
    measure_module: Any = None,
    measurement_duration_s: Optional[float] = None,
    sample_interval_s: Optional[float] = None,
    duck_torque_pct: Optional[float] = None,
) -> ProbeExecutor:
    """
    Return ProbeExecutor(cell_id, z_mm, rpm) -> mean torque %.

    Caller must position the CNC at (cell, z_mm) before the probe loop.
    Does not modify measure_torque_fn internals; optionally scopes duration globals.
    """

    def probe(cell_id: int, z_mm: float, rpm: float) -> Optional[float]:
        @contextmanager
        def _maybe_duration():
            if measurement_duration_s is not None and measure_module is not None:
                with scoped_measurement_duration(
                    measure_module,
                    duration_s=measurement_duration_s,
                    sample_interval_s=sample_interval_s,
                ):
                    yield
            else:
                yield

        with _maybe_duration():
            duck_kw = {}
            if duck_torque_pct is not None and float(duck_torque_pct) > 0:
                duck_kw["duck_above_pct_on_first_sample"] = float(duck_torque_pct)
            measurements = measure_torque_fn(client, rpm, z_mm, **duck_kw)
        return mean_torque_from_measurements(measurements)

    return probe
