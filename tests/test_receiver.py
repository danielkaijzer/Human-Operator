"""Smoke tests for the Flask hardware gateway in simulation (relay-only) mode.

receiver.py configures its hardware at import time from environment variables,
so the module is imported once per test session with the environment pinned to
relay mode and a nonexistent serial port. That guarantees SIMULATED mode on any
machine — including a developer laptop with a real relay plugged in.
"""

import importlib
import os
import sys

import pytest

EMS_COMMAND = {
    "type": "EMS",
    "channel": 1,
    "amplitude": 60,
    "duration": 0.1,
    "frequency": 100,
    "pulse_width": 1000,
}


@pytest.fixture(scope="session")
def receiver_module():
    os.environ["HARDWARE_MODE"] = "relay"
    os.environ["RELAY_PORT"] = "/dev/nonexistent-test-port"
    os.environ.pop("STIM_PORT", None)
    os.environ.pop("ENABLE_STIM", None)

    sys.modules.pop("utils.receiver", None)
    module = importlib.import_module("utils.receiver")
    yield module
    sys.modules.pop("utils.receiver", None)


@pytest.fixture()
def client(receiver_module):
    receiver_module.app.config["TESTING"] = True
    with receiver_module.app.test_client() as test_client:
        yield test_client


class TestHealth:
    def test_health_reports_relay_mode_simulated(self, client):
        response = client.get("/health")
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "ready"
        assert payload["hardware_mode"] == "relay"
        assert payload["relay_hardware_connected"] is False
        assert payload["stim_hardware_connected"] is False
        assert payload["stim_port"] == "SIMULATED"


class TestExecute:
    def test_relay_command_executes_in_simulation(self, client):
        response = client.post(
            "/execute",
            json={"0.0": [{"type": "RELAY", "finger": "index"}]},
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["status"] == "executed"
        assert payload["hardware_mode"]["relay"] == "SIMULATED"

    def test_ems_command_is_skipped_in_relay_mode(self, client):
        response = client.post(
            "/execute",
            json={"0.0": [{"type": "RELAY", "finger": "middle"}, EMS_COMMAND]},
        )

        assert response.status_code == 200
        assert response.get_json()["status"] == "executed"

    def test_full_transformed_payload_shape_is_accepted(self, client):
        # The exact shape app.py produces via transform_actions_to_receiver_format.
        payload = {
            "0.0": [{"type": "RELAY", "finger": "index"}, EMS_COMMAND],
            "0.1": [{"type": "RELAY", "finger": "x"}],
        }
        response = client.post("/execute", json=payload)

        assert response.status_code == 200
        assert response.get_json()["status"] == "executed"

    def test_malformed_payload_returns_error_not_crash(self, client):
        response = client.post("/execute", json=["not", "a", "dict"])

        assert response.status_code == 500
        assert "error" in response.get_json()
