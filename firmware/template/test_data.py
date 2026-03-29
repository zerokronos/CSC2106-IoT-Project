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
    {
        "node_id": 2,
        "msg_type": 1,
        "temp": 28.4,
        "smoke": 0.02,
        "fire": 0,
        "description": "Normal reading"
    },
    {
        "node_id": 1,
        "msg_type": 1,
        "temp": 22.5,
        "smoke": 80.1,
        "fire": 0,
        "description": "High smoke level (80.1 PPM)"
    },
    {
        "node_id": 2,
        "msg_type": 1,
        "temp": 28.4,
        "smoke": 0.02,
        "fire": 0,
        "description": "Back to normal"
    },
    {
        "node_id": 5,
        "msg_type": 1,
        "temp": 60.0,
        "smoke": 0.3,
        "fire": 0,
        "description": "High temperature (60.0 C)"
    },
    {
        "node_id": 2,
        "msg_type": 1,
        "temp": 28.4,
        "smoke": 0.02,
        "fire": 0,
        "description": "Back to normal"
    },
    {
        "node_id": 6,
        "msg_type": 1,
        "temp": 25.0,
        "smoke": 100.0,
        "fire": 0,
        "description": "High smoke (100.0 PPM)"
    },
    {
        "node_id": 3,
        "msg_type": 1,
        "temp": 65.5,
        "smoke": 110.0,
        "fire": 1,
        "description": "CRITICAL: High Temp, High Smoke & Fire Detected"
    },
]
