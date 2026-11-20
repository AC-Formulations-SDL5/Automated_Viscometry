"""Unit tests for wash scrub params and wash-trial helpers."""

from __future__ import annotations

import pytest

from viscometry.run.controller import _resolve_scrub_params
from viscometry.run import settings as run_settings


def test_resolve_scrub_params_defaults():
    feed, count, dwell = _resolve_scrub_params()
    assert feed == run_settings.WASH_SCRUB_FEED
    assert count == run_settings.WASH_SCRUB_COUNT
    assert dwell == run_settings.WASH_SCRUB_DWELL_S


def test_resolve_scrub_params_fast_scrub():
    feed, count, dwell = _resolve_scrub_params(fast_scrub=True)
    assert feed == run_settings.WASH_SCRUB_FEED_FAST
    assert count == run_settings.WASH_SCRUB_COUNT
    assert dwell == run_settings.WASH_SCRUB_DWELL_S_FAST


def test_resolve_scrub_params_explicit_overrides_fast():
    feed, count, dwell = _resolve_scrub_params(
        scrub_feed=2500,
        scrub_count=8,
        scrub_dwell_s=0.25,
        fast_scrub=True,
    )
    assert feed == 2500
    assert count == 8
    assert dwell == 0.25


def test_resolve_scrub_params_rejects_invalid():
    with pytest.raises(ValueError):
        _resolve_scrub_params(scrub_feed=50)
    with pytest.raises(ValueError):
        _resolve_scrub_params(scrub_count=0)
    with pytest.raises(ValueError):
        _resolve_scrub_params(scrub_dwell_s=-1)


def test_wash_trial_settings_present():
    assert run_settings.WASH_TRIAL_DIP_OFFSET_MM == 0.2
    assert run_settings.WASH_TRIAL_DIP_DWELL_S > 0
    assert run_settings.WASH_SCRUB_FEED_FAST > run_settings.WASH_SCRUB_FEED
