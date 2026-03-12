const nodes = new Map();
const alerts = [];
const history = {
  flat01: [],
  flat02: [],
  flat03: [],
};
const anomalyCooldown = {
  flat01: 0,
  flat02: 0,
  flat03: 0,
};

const nodesBody = document.getElementById("nodes-body");
const alertsFeed = document.getElementById("alerts-feed");
const neighborBody = document.getElementById("neighbor-body");
const connStatus = document.getElementById("conn-status");

const severityClass = (value) => {
  if (value === "alarm") return "alarm";
  if (value === "warn") return "warn";
  return "ok";
};

const isActiveAlert = (value) => value && value !== "-";

const effectiveMode = (node) => {
  if (isActiveAlert(node.current_alert) && node.last_alert_mode) {
    return node.last_alert_mode;
  }
  return node.last_telemetry_mode || node.mode || "-";
};

const fmt = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
};

function updateHistory(nodeId, tempValue) {
  if (!(nodeId in history) || tempValue === null || tempValue === undefined) return;
  const t = Date.now();
  history[nodeId].push({ t, temp: Number(tempValue) });
  if (history[nodeId].length > 30) history[nodeId].shift();
}

function computeNeighborRows() {
  const flats = ["flat01", "flat02", "flat03"];
  return flats.map((flatId) => {
    const row = history[flatId];
    const latest = row[row.length - 1];

    const others = flats.filter((f) => f !== flatId);
    const otherTemps = others
      .map((id) => history[id][history[id].length - 1])
      .filter(Boolean)
      .map((x) => x.temp);

    const neighborMean = otherTemps.length
      ? otherTemps.reduce((a, b) => a + b, 0) / otherTemps.length
      : null;

    let slope = 0;
    if (row.length >= 2) {
      const a = row[row.length - 2];
      const b = row[row.length - 1];
      const dt = (b.t - a.t) / 1000;
      if (dt > 0) slope = (b.temp - a.temp) / dt;
    }

    const isAnomaly =
      latest &&
      neighborMean !== null &&
      latest.temp > neighborMean + 0.8 &&
      slope > 0.05;

    return {
      flatId,
      temp: latest ? latest.temp : null,
      slope,
      neighborMean,
      isAnomaly,
    };
  });
}

function renderNodes() {
  const rows = [...nodes.values()].sort((a, b) => a.node_id.localeCompare(b.node_id));
  nodesBody.innerHTML = rows
    .map(
      (n) => `
      <tr>
        <td>${n.node_id || "-"}</td>
        <td>${effectiveMode(n)}</td>
        <td><span class="tag ${severityClass(n.status)}">${n.status || "-"}</span></td>
        <td>${n.last_seen || "-"}</td>
        <td>${fmt(n.temp_c, 2)}</td>
        <td>${fmt(n.smoke, 3)}</td>
        <td>${n.current_alert || "-"}</td>
      </tr>
    `,
    )
    .join("");
}

function renderAlerts() {
  alertsFeed.innerHTML = alerts
    .slice(0, 50)
    .map(
      (a) => `
      <li>
        <strong>[${a.severity || "none"}]</strong> ${a.ts || ""} - ${a.node_id || ""} ${a.reason || ""}
      </li>
    `,
    )
    .join("");
}

function renderNeighbors() {
  const rows = computeNeighborRows();
  neighborBody.innerHTML = rows
    .map(
      (r) => `
      <tr>
        <td>${r.flatId}</td>
        <td>${fmt(r.temp, 2)}</td>
        <td>${fmt(r.slope, 3)}</td>
        <td>${fmt(r.neighborMean, 2)}</td>
        <td><span class="tag ${r.isAnomaly ? "alarm" : "ok"}">${r.isAnomaly ? "yes" : "no"}</span></td>
      </tr>
    `,
    )
    .join("");

  const nowMs = Date.now();
  const anomalous = rows.filter((r) => r.isAnomaly);
  anomalous.forEach((row) => {
    if (nowMs - anomalyCooldown[row.flatId] < 15000) return;
    anomalyCooldown[row.flatId] = nowMs;
    alerts.unshift({
      node_id: row.flatId,
      ts: new Date().toISOString(),
      severity: "warn",
      reason: "neighbor_anomaly_dashboard",
    });
  });
  if (anomalous.length > 0) {
    while (alerts.length > 50) alerts.pop();
    renderAlerts();
  }
}

function applyMessage(topic, payload) {
  if (!payload || !payload.node_id) return;
  const isAlert = topic.includes("/alert/");
  const isTelemetry = topic.includes("/telemetry/") || topic.includes("/heartbeat/");

  const prev = nodes.get(payload.node_id) || {
    node_id: payload.node_id,
    mode: "",
    last_telemetry_mode: "",
    last_alert_mode: "",
    status: "unknown",
    last_seen: "",
    temp_c: null,
    smoke: null,
    current_alert: "",
  };

  const next = {
    ...prev,
    ...payload,
    status: payload.status || prev.status,
    last_seen: payload.ts || prev.last_seen,
    current_alert:
      isAlert
        ? payload.reason || payload.severity || "alert"
        : prev.current_alert,
  };

  if (isTelemetry && payload.mode) {
    next.last_telemetry_mode = payload.mode;
    next.mode = payload.mode;
  } else if (isAlert && payload.mode) {
    next.last_alert_mode = payload.mode;
    next.mode = prev.mode || prev.last_telemetry_mode || payload.mode;
  } else {
    next.mode = prev.mode || prev.last_telemetry_mode || payload.mode || "";
  }

  nodes.set(payload.node_id, next);
  updateHistory(payload.node_id, payload.temp_c);

  if (isAlert) {
    alerts.unshift({
      node_id: payload.node_id,
      ts: payload.ts,
      severity: payload.severity,
      reason: payload.reason,
    });
    while (alerts.length > 50) alerts.pop();
  }

  renderNodes();
  renderAlerts();
  renderNeighbors();
}

function applySnapshot(snapshot) {
  (snapshot.nodes || []).forEach((n) => {
    const mode = n.mode || "";
    nodes.set(n.node_id, {
      ...n,
      mode,
      last_telemetry_mode: n.last_telemetry_mode || mode,
      last_alert_mode: n.last_alert_mode || "",
    });
    updateHistory(n.node_id, n.temp_c);
  });

  (snapshot.alerts || []).forEach((a) => alerts.push(a));
  while (alerts.length > 50) alerts.pop();

  renderNodes();
  renderAlerts();
  renderNeighbors();
}

function connectSse() {
  const source = new EventSource("/events");

  source.addEventListener("open", () => {
    connStatus.textContent = "Connected (SSE)";
  });

  source.addEventListener("snapshot", (event) => {
    const data = JSON.parse(event.data);
    applySnapshot(data);
  });

  source.addEventListener("mqtt", (event) => {
    const data = JSON.parse(event.data);
    applyMessage(data.topic || "", data.payload || {});
  });

  source.addEventListener("error", () => {
    connStatus.textContent = "Disconnected, retrying...";
  });
}

connectSse();
