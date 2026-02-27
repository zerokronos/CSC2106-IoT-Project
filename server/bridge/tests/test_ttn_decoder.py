import base64

import pytest

from ttn_decoder import TTNDecodeError, decode_binary_payload, parse_uplink


def test_decode_binary_payload_success() -> None:
    raw = bytes([2, 1, 0x01, 0x1C, 0x00, 0x02, 0x02])
    frm_payload = base64.b64encode(raw).decode("ascii")

    decoded = decode_binary_payload(frm_payload)

    assert decoded["node_id"] == 2
    assert decoded["msg_type"] == 1
    assert decoded["temp_c"] == 28.4
    assert decoded["smoke"] == 0.02
    assert decoded["severity"] == 2


def test_decode_binary_payload_rejects_short_input() -> None:
    frm_payload = base64.b64encode(bytes([1, 1, 0])).decode("ascii")

    with pytest.raises(TTNDecodeError):
        decode_binary_payload(frm_payload)


def test_parse_ttn_with_frm_payload() -> None:
    raw = bytes([9, 3, 0x00, 0xFA, 0x00, 0x32, 0x01])
    frm_payload = base64.b64encode(raw).decode("ascii")

    body = {
        "end_device_ids": {"device_id": "lab-node-9"},
        "received_at": "2026-02-27T10:00:00Z",
        "uplink_message": {"frm_payload": frm_payload},
    }

    decoded = parse_uplink(body)

    assert decoded.node_id == 9
    assert decoded.msg_type == 3
    assert decoded.temp_c == 25.0
    assert decoded.smoke == 0.5
    assert decoded.severity == 1


def test_parse_dev_json_format() -> None:
    body = {
        "node_id": "flat01",
        "msg_type": "telemetry",
        "temp_c": 29.5,
        "smoke": 0.03,
        "severity": "none",
        "reason": "",
    }

    decoded = parse_uplink(body)

    assert decoded.node_id == "flat01"
    assert decoded.msg_type == "telemetry"
    assert decoded.temp_c == 29.5
    assert decoded.smoke == 0.03


def test_parse_rejects_unknown_format() -> None:
    with pytest.raises(TTNDecodeError):
        parse_uplink({"foo": "bar"})
