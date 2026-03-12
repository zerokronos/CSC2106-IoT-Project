"""Local TTN-to-MQTT bridge with SSE dashboard feed."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse

from config import settings
from contract import TOPIC_SYSTEM_LOGS, make_contract_payload, message_route, severity_name, topic_for
from mqtt_service import MQTTService
from state import StateStore
from ttn_decoder import TTNDecodeError, parse_uplink

app = FastAPI(title="CSC2106 Local Bridge", version="0.1.0")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _dashboard_dir() -> Path:
    return _project_root() / "dashboard" / "mvp"


class SSEHub:
    def __init__(self) -> None:
        self.clients: set[asyncio.Queue[dict[str, Any]]] = set()

    def register(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        self.clients.add(queue)
        return queue

    def unregister(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.clients.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        stale: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in self.clients:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.clients.discard(queue)


def _make_status(route: str, severity: Any, smoke: float | None) -> str:
    named = severity_name(severity)
    if route == "alert" or named == "alarm":
        return "alarm"
    if named == "warn":
        return "warn"
    if smoke is not None and smoke > 0.7:
        return "warn"
    return "ok"


def _encode_sse(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, separators=(",", ":"))}\n\n"


@app.on_event("startup")
def on_startup() -> None:
    app.state.loop = asyncio.get_running_loop()
    app.state.hub = SSEHub()
    app.state.store = StateStore()

    def _on_mqtt_message(topic: str, payload: dict[str, Any]) -> None:
        app.state.store.apply_message(topic, payload)

        event = {
            "topic": topic,
            "payload": payload,
        }
        app.state.loop.call_soon_threadsafe(app.state.hub.publish, event)

    app.state.mqtt = MQTTService(on_message=_on_mqtt_message)
    app.state.mqtt.start()

    startup_log = make_contract_payload(
        node_id="system",
        mode="wifi",
        ts=None,
        status="ok",
        severity="none",
        reason="bridge_started",
        values={"http_port": settings.bridge_http_port},
        meta={"source": "bridge"},
    )
    app.state.mqtt.publish_json(TOPIC_SYSTEM_LOGS, startup_log)


@app.on_event("shutdown")
def on_shutdown() -> None:
    app.state.mqtt.stop()


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "mqtt_host": settings.mqtt_host,
        "mqtt_port": settings.mqtt_port,
        "dashboard": "/dashboard",
    }


@app.get("/dashboard")
def dashboard_index() -> FileResponse:
    index_file = _dashboard_dir() / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="dashboard file not found")
    return FileResponse(index_file)


@app.get("/dashboard/app.js")
def dashboard_js() -> FileResponse:
    js_file = _dashboard_dir() / "app.js"
    if not js_file.exists():
        raise HTTPException(status_code=404, detail="dashboard JS file not found")
    return FileResponse(js_file, media_type="application/javascript")


@app.get("/dashboard/styles.css")
def dashboard_css() -> FileResponse:
    css_file = _dashboard_dir() / "styles.css"
    if not css_file.exists():
        raise HTTPException(status_code=404, detail="dashboard CSS file not found")
    return FileResponse(css_file, media_type="text/css")


@app.get("/api/state")
def api_state() -> dict[str, Any]:
    return app.state.store.snapshot()


@app.get("/events")
async def events(request: Request) -> StreamingResponse:
    queue = app.state.hub.register()

    async def stream() -> Any:
        try:
            snapshot = app.state.store.snapshot()
            yield _encode_sse("snapshot", snapshot)

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _encode_sse("mqtt", event)
                except asyncio.TimeoutError:
                    yield _encode_sse("ping", {"ok": True})
        finally:
            app.state.hub.unregister(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/ttn/uplink")
async def ttn_uplink(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc

    try:
        decoded = parse_uplink(body)
        route = message_route(decoded.msg_type)
    except TTNDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    severity = decoded.severity
    message = make_contract_payload(
        node_id=decoded.node_id,
        mode="lorawan",
        ts=decoded.ts,
        temp_c=decoded.temp_c,
        smoke=decoded.smoke,
        status=_make_status(route, severity, decoded.smoke),
        severity=severity,
        reason=decoded.reason,
        values={
            "temp_c": decoded.temp_c,
            "smoke": decoded.smoke,
            "msg_type": decoded.msg_type,
            "severity": decoded.severity,
        },
        meta=decoded.meta,
    )

    topic = topic_for(message["node_id"], decoded.msg_type)
    app.state.mqtt.publish_json(topic, message)

    return JSONResponse({"ok": True, "topic": topic, "message": message})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=settings.bridge_http_port, reload=False)
