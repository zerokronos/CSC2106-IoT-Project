import pytest

from contract import make_contract_payload, message_route, normalize_node_id, topic_for


def test_message_route_mapping() -> None:
    assert message_route(1) == "telemetry"
    assert message_route("2") == "heartbeat"
    assert message_route("alert") == "alert"


def test_message_route_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        message_route(7)


def test_normalize_node_id_int() -> None:
    assert normalize_node_id(1) == "node001"
    assert normalize_node_id("7") == "node007"
    assert normalize_node_id("flat02") == "flat02"


def test_topic_for_routes() -> None:
    assert topic_for("flat01", "telemetry") == "csc2106/v0/telemetry/flat01"
    assert topic_for("flat01", 2) == "csc2106/v0/heartbeat/flat01"
    assert topic_for("flat01", 3) == "csc2106/v0/alert/flat01"


def test_contract_payload_has_required_fields() -> None:
    payload = make_contract_payload(
        node_id="flat01",
        mode="wifi",
        ts="2026-02-27T00:00:00Z",
        temp_c=28.0,
        smoke=0.01,
        status="ok",
        severity="none",
        reason="",
        values={"temp_c": 28.0},
        meta={"source": "test"},
    )

    expected = {
        "node_id",
        "ts",
        "mode",
        "temp_c",
        "smoke",
        "status",
        "severity",
        "reason",
        "values",
        "meta",
    }
    assert set(payload.keys()) == expected
