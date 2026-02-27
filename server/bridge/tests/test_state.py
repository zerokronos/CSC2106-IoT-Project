from state import StateStore


def _effective_mode(node: dict[str, object]) -> str:
    current_alert = str(node.get("current_alert", "") or "")
    if current_alert != "-" and current_alert and node.get("last_alert_mode"):
        return str(node["last_alert_mode"])
    return str(node.get("last_telemetry_mode") or node.get("mode") or "")


def test_alert_mode_is_preserved_during_active_alert() -> None:
    store = StateStore()
    node_id = "flat02"

    store.apply_message(
        f"csc2106/v0/telemetry/{node_id}",
        {
            "node_id": node_id,
            "mode": "wifi",
            "status": "ok",
            "ts": "2026-02-27T14:00:00Z",
            "temp_c": 28.2,
            "smoke": 0.02,
        },
    )
    store.apply_message(
        f"csc2106/v0/alert/{node_id}",
        {
            "node_id": node_id,
            "mode": "lorawan",
            "status": "alarm",
            "severity": "alarm",
            "reason": "smoke_high",
            "ts": "2026-02-27T14:00:05Z",
            "temp_c": 32.1,
            "smoke": 0.85,
        },
    )
    store.apply_message(
        f"csc2106/v0/telemetry/{node_id}",
        {
            "node_id": node_id,
            "mode": "wifi",
            "status": "warn",
            "ts": "2026-02-27T14:00:10Z",
            "temp_c": 31.7,
            "smoke": 0.4,
        },
    )

    snapshot = store.snapshot()
    node = next(x for x in snapshot["nodes"] if x["node_id"] == node_id)

    assert node["mode"] == "wifi"
    assert node["last_telemetry_mode"] == "wifi"
    assert node["last_alert_mode"] == "lorawan"
    assert node["current_alert"] == "smoke_high"
    assert _effective_mode(node) == "lorawan"
