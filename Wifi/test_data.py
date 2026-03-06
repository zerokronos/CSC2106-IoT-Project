# Test data extracted from server/bridge/tests/
# These are the actual sensor values used in the test suite

TEST_SENSOR_DATA = [
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
