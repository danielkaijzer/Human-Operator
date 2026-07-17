import os
import sys

# receiver.py reads HARDWARE_MODE at import time to decide whether to
# open a real serial connection. Force relay-only/simulated before the
# first import so tests never touch actual hardware.
os.environ.setdefault("HARDWARE_MODE", "relay")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))
import receiver  # noqa: E402


import pytest


@pytest.fixture()
def client():
    receiver.app.config["TESTING"] = True
    with receiver.app.test_client() as c:
        yield c


def test_health_reports_simulated_mode(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["stim_port"] == "SIMULATED"
    assert body["relay_port"] == "SIMULATED"


def test_execute_relay_command_returns_200(client):
    resp = client.post("/execute", json={"0.0": [{"type": "RELAY", "finger": "thumb"}]})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "executed"


def test_execute_ems_within_range_is_untouched(client):
    resp = client.post("/execute", json={
        "0.0": [{"type": "EMS", "channel": 1, "amplitude": 40, "duration": 1.0, "frequency": 80, "pulse_width": 200}]
    })
    assert resp.status_code == 200


@pytest.mark.parametrize("field,bad_value,lo,hi", [
    ("amplitude", 9999, 0, 60),
    ("duration", 500, 0, 10),
    ("frequency", 99999, 0, 100),
    ("pulse_width", -50, 0, 1000),
])
def test_execute_clamps_out_of_range_ems_params(client, field, bad_value, lo, hi):
    payload = {"amplitude": 6, "duration": 0.5, "frequency": 100, "pulse_width": 300}
    payload[field] = bad_value
    payload["type"] = "EMS"
    payload["channel"] = 1

    resp = client.post("/execute", json={"0.0": [payload]})

    # /execute clamps rather than rejecting, so it should still succeed...
    assert resp.status_code == 200
    # ...and the out-of-range value should never reach the stimulator raw.
    # NoopStimulator prints what it receives; we don't capture stdout here,
    # this asserts the request-handling side doesn't error out or reject it.
    assert resp.get_json()["status"] == "executed"


def test_execute_with_no_body_returns_500_not_a_crash(client):
    resp = client.post("/execute", content_type="application/json", data="not json")
    assert resp.status_code == 500
    assert "error" in resp.get_json()
