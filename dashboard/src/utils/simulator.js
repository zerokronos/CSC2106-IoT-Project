// ─── CONSTANTS ───────────────────────────────────────────────────────────────
export const NODE_IDS = ['flat01','flat02','flat03','flat04','flat05','flat06']

export const NODE_COLORS = {
  flat01: '#00d4ff',
  flat02: '#22c55e',
  flat03: '#f97316',
  flat04: '#a78bfa',
  flat05: '#f472b6',
  flat06: '#facc15',
}

export const ANOMALY_NODE = 'flat03'
export const TEMP_ALARM   = 40
export const SMOKE_ALARM  = 0.7

// ─── INITIAL STATE FACTORY ───────────────────────────────────────────────────
export function makeInitialNodes() {
  const nodes = {}
  NODE_IDS.forEach(id => {
    nodes[id] = {
      id,
      online:      true,
      mode:        'wifi',   // 'wifi' | 'lora' | 'offline'
      temp:        25 + Math.random() * 3,
      smoke:       0.10 + Math.random() * 0.05,
      lastSeen:    Date.now(),
      alertActive: false,
    }
  })
  return nodes
}

// ─── TICK — call once per second to advance simulation ───────────────────────
// Returns { nodes, newAlerts }  (immutable update)
export function simulateTick(nodes, tickRef) {
  tickRef.current += 1
  const tick = tickRef.current
  const baselineDrift = Math.sin(tick / 120) * 0.8

  const next   = { ...nodes }
  const newAlerts = []

  NODE_IDS.forEach(id => {
    const n = { ...nodes[id] }
    if (!n.online) { next[id] = n; return }

    // temperature drift
    let delta = (Math.random() - 0.5) * 0.4 + baselineDrift * 0.05
    if (id === ANOMALY_NODE && tick > 20) delta += 0.15   // anomaly trend
    n.temp  = Math.max(20, Math.min(60, n.temp + delta))

    // smoke
    n.smoke = Math.max(0, Math.min(1, n.smoke + (Math.random() - 0.5) * 0.02))
    if (n.temp > 38) n.smoke = Math.min(1, n.smoke + 0.05)

    // alerts
    const wasAlert  = n.alertActive
    n.alertActive   = n.temp > TEMP_ALARM || n.smoke > SMOKE_ALARM
    if (n.alertActive && !wasAlert) {
      newAlerts.push({
        sev:  'high',
        msg:  `${id.toUpperCase()}: THRESHOLD BREACH — Temp ${n.temp.toFixed(1)}°C, Smoke ${n.smoke.toFixed(2)}`,
        time: new Date().toLocaleTimeString(),
      })
    }

    n.lastSeen = Date.now()
    next[id]   = n
  })

  // periodic heartbeat alert
  if (tick % 30 === 0) {
    const online = NODE_IDS.filter(id => next[id].online).length
    newAlerts.push({
      sev:  'info',
      msg:  `Heartbeat OK — ${online}/6 nodes reporting`,
      time: new Date().toLocaleTimeString(),
    })
  }

  return { nodes: next, newAlerts }
}

// ─── NORMALISE — swap this out when real MQTT arrives ────────────────────────
// Person C might use different field names — adapt only THIS function.
//
// Expected incoming shape (agree with Person C):
// { node_id, temp, smoke, mode, ts }
//
export function normalise(raw) {
  return {
    id:    raw.node_id  ?? raw.id,
    temp:  raw.temp     ?? raw.temperature,
    smoke: raw.smoke    ?? raw.smoke_level,
    mode:  raw.mode     ?? raw.comm_mode ?? 'wifi',
    ts:    raw.ts       ?? Date.now(),
  }
}
