"""Los tests no alteran energía: la API se sustituye por un registro sintético."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import f0_mantener_activo as energy
import medir_f0 as f0


def test_temporary_protection_only_system_required_and_cleanup_on_exception():
    calls = []
    def setter(flags):
        calls.append(flags)
        return energy.CONTINUOUS
    with pytest.raises(RuntimeError, match="fixture"):
        with energy.ExecutionState(setter) as guard:
            guard.refresh()
            raise RuntimeError("fixture")
    assert calls == [energy.CONTINUOUS | energy.SYSTEM_REQUIRED,
                     energy.CONTINUOUS | energy.SYSTEM_REQUIRED, energy.CONTINUOUS]
    assert not any(value & 0x2 for value in calls)  # Nunca ES_DISPLAY_REQUIRED.


def test_null_api_return_fails_closed():
    with pytest.raises(OSError, match="NULL"):
        with energy.ExecutionState(lambda flags: 0):
            pytest.fail("No debe entrar con API fallida")


def test_sleep_events_invalidate_without_publishing_user_or_device(monkeypatch):
    monkeypatch.setattr(f0, "run", lambda *a, **kw: '{"aplica":true,"kernel_power_42":[{"id":42,"utc":"2026-11-14T15:00:01Z"}],"power_troubleshooter_1":[]}')
    result = f0.windows_sleep_events("2026-11-14T10:59:00-04:00", "2026-11-14T11:01:00-04:00")
    assert result["suspension_detectada"] is True


def test_resume_interval_overlap_is_detected_without_kernel_event(monkeypatch):
    monkeypatch.setattr(f0, "run", lambda *a, **kw: '{"aplica":true,"kernel_power_42":[],"power_troubleshooter_1":[{"datos":{"SleepTime":"2026-11-14T15:00:01Z","WakeTime":"2026-11-14T15:00:30Z"}}]}')
    assert f0.windows_sleep_events("2026-11-14T10:59:00-04:00", "2026-11-14T11:01:00-04:00")["suspension_detectada"] is True
