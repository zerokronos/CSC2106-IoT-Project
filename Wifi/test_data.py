# Test data extracted from server/bridge/tests/
# These are the actual sensor values used in the test suite

TEST_SENSOR_DATA = [
    # From test_ttn_decoder.py - test_decode_binary_payload_success()
    {
        "node_id": 2,
        "msg_type": 1,  # Telemetry
        "temp": 28.4,
        "smoke": 0.02,
        "fire": 0,
        "description": "Test case 1: Normal reading"
    },
    # From test_ttn_decoder.py - test_parse_ttn_with_frm_payload()
    {
        "node_id": 9,
        "msg_type": 3,  # Alert
        "temp": 25.0,
        "smoke": 0.5,
        "fire": 0,
        "description": "Test case 2: High smoke level (alert)"
    },
    # Additional realistic test case
    {
        "node_id": 1,
        "msg_type": 1,  # Telemetry
        "temp": 22.5,
        "smoke": 0.1,
        "fire": 0,
        "description": "Test case 3: Low temperature, low smoke"
    },
    # High temperature scenario
    {
        "node_id": 5,
        "msg_type": 1,  # Telemetry
        "temp": 35.0,
        "smoke": 0.3,
        "fire": 0,
        "description": "Test case 4: High temperature, medium smoke"
    },
]
