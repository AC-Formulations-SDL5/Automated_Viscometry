"""Replay CSV rows through LiveCellSession; compare with batch live_adapter."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.rheology.live_adapter import predict_cell_rheology
from viscometry.rheology.live_engine import CharacterizationManager

PEG_CSV = _ROOT / "results" / "Auto-runs" / "all_PEG.csv"
TOL_MU_REL = 0.05
TOL_N = 0.15


def _measurement_rows_from_df(df: pd.DataFrame, cell_id: int) -> list:
    sub = df[df["cell"] == cell_id].copy()
    rows = []
    for _, r in sub.iterrows():
        rows.append(
            {
                "cell_id": int(cell_id),
                "rpm": float(r["RPM"]),
                "height": float(r["Z_Height_mm"]),
                "rotational_drag": float(r["Rotational_Drag"]),
                "torque_percent": float(r["Torque_%"]),
                "timestamp": float(r.get("Elapsed_Time_s", 0) or 0),
            }
        )
    return rows


def _replay_cell_through_engine(df: pd.DataFrame, cell_id: int) -> dict:
    sub = df[df["cell"] == cell_id]
    rpms = sorted(sub["RPM"].unique())
    mgr = CharacterizationManager(torque_floor_pct=0.0)
    mgr.start_cell(cell_id, rpms)

    z_levels = sorted(sub["Z_Height_mm"].unique(), reverse=True)
    for z in z_levels:
        z_rows = sub[np.isclose(sub["Z_Height_mm"], z)]
        for rpm in rpms:
            rpm_rows = z_rows[np.isclose(z_rows["RPM"], rpm)]
            if rpm_rows.empty:
                continue
            # Match live_adapter.filter_measurement_points: latest timestamp per height.
            last = rpm_rows.sort_values("Elapsed_Time_s").iloc[-1]
            mgr.ingest_point(
                cell_id,
                float(last["Z_Height_mm"]),
                float(last["RPM"]),
                float(last["Torque_%"]),
                timestamp=float(last.get("Elapsed_Time_s", 0) or 0),
            )
        mgr.on_z_slice_complete(cell_id, float(z))

    events = mgr.finalize_cell(cell_id)
    summary_events = [e for e in events if e.get("type") == "summary"]
    return summary_events[0] if summary_events else {}


class TestLiveEngineReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PEG_CSV.is_file():
            raise unittest.SkipTest(f"PEG CSV not found: {PEG_CSV}")
        cls.df = pd.read_csv(PEG_CSV)

    def test_replay_cell1_single_rpm_matches_batch(self):
        cell_id = 1
        live_summary = _replay_cell_through_engine(self.df, cell_id)
        batch_rows = _measurement_rows_from_df(self.df, cell_id)
        rpms = sorted(self.df[self.df.cell == cell_id]["RPM"].unique())
        _per, batch_summary = predict_cell_rheology(
            cell_id, rpms, batch_rows, torque_floor_pct=0.0, hit_point_z=None
        )
        self.assertTrue(live_summary.get("success"))
        self.assertTrue(batch_summary.get("success"))
        live_mu = live_summary.get("mu_app_cP")
        batch_mu = batch_summary.get("mu_app_cP")
        self.assertIsNotNone(live_mu)
        self.assertIsNotNone(batch_mu)
        rel_err = abs(live_mu - batch_mu) / max(abs(batch_mu), 1e-9)
        self.assertLess(rel_err, TOL_MU_REL, f"mu live={live_mu} batch={batch_mu}")

    def test_replay_cell2_multi_rpm_matches_batch(self):
        cell_id = 2
        live_summary = _replay_cell_through_engine(self.df, cell_id)
        batch_rows = _measurement_rows_from_df(self.df, cell_id)
        rpms = sorted(self.df[self.df.cell == cell_id]["RPM"].unique())
        _per, batch_summary = predict_cell_rheology(
            cell_id, rpms, batch_rows, torque_floor_pct=0.0, hit_point_z=None
        )
        self.assertTrue(live_summary.get("success"), live_summary.get("error"))
        self.assertTrue(batch_summary.get("success"), batch_summary.get("error"))
        live_n = live_summary.get("n_idx")
        batch_n = batch_summary.get("n")
        if live_n is not None and batch_n is not None:
            self.assertLess(abs(live_n - batch_n), TOL_N, f"n live={live_n} batch={batch_n}")
        if live_summary.get("K_stress") and batch_summary.get("K_Pas_n"):
            self.assertTrue(np.isfinite(live_summary["K_stress"]))


if __name__ == "__main__":
    unittest.main()
