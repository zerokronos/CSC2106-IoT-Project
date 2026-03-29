import { useState, useEffect, useRef, useCallback } from 'react'
import {
  NODE_IDS, makeInitialNodes, simulateTick, normalise,
  TEMP_ALARM, SMOKE_ALARM,
} from '../utils/simulator'

// ─── TOGGLE THIS when the real broker is ready ───────────────────────────────
const USE_REAL_MQTT   = true
const MQTT_BROKER_URL = `ws://${window.location.hostname}:9001` // Dynamically use the Pi's IP
// ─────────────────────────────────────────────────────────────────────────────

const MAX_HISTORY = 60
const MAX_ALERTS  = 30

const STORAGE_KEY = 'csc2106_known_nodes'

function loadPersistedNodes() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return {}
    const parsed = JSON.parse(saved)
    // Restore all previously seen nodes as offline — live MQTT will update them
    const seeded = {}
    Object.keys(parsed).forEach(id => {
      seeded[id] = { ...parsed[id], online: false, mode: 'offline', alertActive: false }
    })
    return seeded
  } catch {
    return {}
  }
}

export function useDashboard() {
  const [nodes,   setNodes]   = useState(() => (USE_REAL_MQTT ? loadPersistedNodes() : makeInitialNodes()))
  const [history, setHistory] = useState(() => (USE_REAL_MQTT ? {} : Object.fromEntries(NODE_IDS.map(id => [id, []]))))
  const [alerts,  setAlerts]  = useState([])
  const tickRef    = useRef(0)
  const mqttRef    = useRef(null)
  const nodesRef   = useRef({})

  const makeNode = useCallback((id) => ({
    id,
    online: true,
    mode: 'wifi',
    temp: 0,
    smoke: 0,
    lastSeen: Date.now(),
    alertActive: false,
    fireDetected: false,
  }), [])

  // ── push alert helper ──────────────────────────────────────────────────────
  const pushAlerts = useCallback((incoming) => {
    if (!incoming.length) return
    setAlerts(prev => [...incoming, ...prev].slice(0, MAX_ALERTS))
  }, [])

  // ── map severity levels for bridge payload ─────────────────────────────────
  const mapSeverity = useCallback((severity) => {
    const value = String(severity ?? '').toLowerCase()
    if (value === 'alarm' || value === 'high' || value === 'critical' || value === '2') return 'high'
    if (value === 'warn' || value === 'warning' || value === 'med' || value === 'medium' || value === '1') return 'med'
    return 'info'
  }, [])

  // ── append history helper ──────────────────────────────────────────────────
  const appendHistory = useCallback((updatedNodes) => {
    setHistory(prev => {
      const next      = { ...prev }
      const timestamp = USE_REAL_MQTT ? Date.now() : tickRef.current

      Object.keys(updatedNodes).forEach(id => {
        const n = updatedNodes[id]
        if (!n.online) return
        const series = prev[id] ?? []
        next[id] = [
          ...series,
          { t: timestamp, temp: n.temp, smoke: n.smoke },
        ].slice(-MAX_HISTORY)
      })
      return next
    })
  }, [])

  // ── SIMULATION mode ────────────────────────────────────────────────────────
  useEffect(() => {
    if (USE_REAL_MQTT) return

    // prime 30 ticks of history on mount
    let primed = makeInitialNodes()
    const primedHistory = {}
    NODE_IDS.forEach(id => { primedHistory[id] = [] })

    for (let i = 0; i < 30; i++) {
      tickRef.current++
      const { nodes: n } = simulateTick(primed, tickRef)
      primed = n
      NODE_IDS.forEach(id => {
        primedHistory[id] = [
          ...primedHistory[id],
          { t: tickRef.current, temp: n[id].temp, smoke: n[id].smoke },
        ].slice(-MAX_HISTORY)
      })
    }
    setNodes(primed)
    setHistory(primedHistory)

    // live tick every second
    const interval = setInterval(() => {
      setNodes(prev => {
        const { nodes: next, newAlerts } = simulateTick(prev, tickRef)
        pushAlerts(newAlerts)
        return next
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [appendHistory, pushAlerts])

  // ── REAL MQTT mode ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!USE_REAL_MQTT) return

    // dynamic import so mqtt doesn't get bundled unless needed
    import('mqtt').then((mqtt) => {
      const connect = mqtt.connect || mqtt.default?.connect
      const client = connect(MQTT_BROKER_URL)
      mqttRef.current = client

      client.on('connect', () => {
        pushAlerts([{ sev:'info', msg:'MQTT connected to broker', time: new Date().toLocaleTimeString() }])
        // WiFi primary path topics
        client.subscribe('telemetry/#')
        client.subscribe('alert/#')
        client.subscribe('heartbeat/#')
        // LoRa fallback bridge path topics (csc2106/v0/...)
        client.subscribe('csc2106/v0/telemetry/#')
        client.subscribe('csc2106/v0/alert/#')
        client.subscribe('csc2106/v0/heartbeat/#')
      })

      client.on('message', (topic, payload) => {
        try {
          const raw  = JSON.parse(payload.toString())
          const data = normalise(raw)
          const topicId = topic.split('/').filter(Boolean).pop()
          const id = data.id ?? topicId
          if (!id) return

          if (topic.includes('/telemetry/') || topic.startsWith('telemetry/')) {
            // Compute alerts BEFORE setNodes using the ref (pure updater, no side effects)
            const existing = nodesRef.current[id] ?? makeNode(id)
            const incomingMode = data.mode ?? (existing.mode === 'offline' ? 'wifi' : (existing.mode ?? 'wifi'))
            const tempVal  = Number(data.temp  ?? existing.temp  ?? 0)
            const smokeVal = Number(data.smoke ?? existing.smoke ?? 0)
            const fireVal  = Boolean(data.fireDetected)

            const isTempAlert  = tempVal  > TEMP_ALARM
            const isSmokeAlert = smokeVal > SMOKE_ALARM
            const isFireAlert  = fireVal

            const wasTempAlert  = Number(existing.temp  ?? 0) > TEMP_ALARM
            const wasSmokeAlert = Number(existing.smoke ?? 0) > SMOKE_ALARM
            const wasFireAlert  = existing.fireDetected
            const wasAlert      = existing.alertActive
            const nextAlertActive = isTempAlert || isSmokeAlert || isFireAlert

            const pendingAlerts = []
            const time = new Date().toLocaleTimeString()
            const displayId = String(id).toUpperCase()

            if ((isTempAlert && !wasTempAlert) || (isSmokeAlert && !wasSmokeAlert) || (isFireAlert && !wasFireAlert)) {
              const cause = []
              if (isTempAlert  && !wasTempAlert)  cause.push(`HIGH TEMP (${tempVal.toFixed(1)}°C)`)
              if (isSmokeAlert && !wasSmokeAlert) cause.push(`HIGH SMOKE (${smokeVal.toFixed(1)} PPM)`)
              if (isFireAlert  && !wasFireAlert)  cause.push('FIRE DETECTED')
              pendingAlerts.push({ sev: 'high', msg: `${displayId} FLAGGED: ${cause.join(' & ')}`, time })
            }

            if (existing.mode !== 'lora' && incomingMode === 'lora') {
              pendingAlerts.push({ sev: 'med', msg: `${displayId}: LORA FALLBACK ACTIVE — WiFi failed, transmitting via LoRaWAN`, time })
            }

            if (wasAlert && !nextAlertActive) {
              pendingAlerts.push({ sev: 'info', msg: `${displayId}: RECOVERED — All thresholds nominal`, time })
            }

            setNodes(prev => {
              const ex = prev[id] ?? makeNode(id)
              return {
                ...prev,
                [id]: {
                  ...ex,
                  ...data,
                  online: true,
                  mode: incomingMode,
                  lastSeen: Date.now(),
                  fireDetected: fireVal,
                  alertActive: nextAlertActive,
                },
              }
            })

            if (pendingAlerts.length) pushAlerts(pendingAlerts)
          }

          if (topic.includes('/alert/') || topic.startsWith('alert/')) {
            pushAlerts([{
              sev:  mapSeverity(raw.severity),
              msg:  raw.msg ?? raw.reason ?? `Alert from ${data.id}`,
              time: new Date().toLocaleTimeString(),
            }])
          }

          if (topic.includes('/heartbeat/') || topic.startsWith('heartbeat/')) {
            setNodes(prev => {
              const existing = prev[id] ?? makeNode(id)
              const n = {
                ...existing,
                lastSeen: Date.now(),
                online: true,
                mode: data.mode || (existing.mode === 'offline' ? 'wifi' : (existing.mode || 'wifi')),
              }
              return { ...prev, [id]: n }
            })
          }
        } catch (e) {
          console.error('MQTT parse error', e)
        }
      })

      client.on('error', (err) => {
        pushAlerts([{ sev:'high', msg:`MQTT error: ${err.message}`, time: new Date().toLocaleTimeString() }])
      })
    })

    return () => mqttRef.current?.end()
  }, [appendHistory, makeNode, pushAlerts])

  // ── EFFECT for HISTORY + nodesRef sync ────────────────────────────────────
  const isInitialMount = useRef(true)
  useEffect(() => {
    nodesRef.current = nodes

    // Skip the initial render to prevent duplicate history on mount
    if (isInitialMount.current) {
      isInitialMount.current = false
    } else {
      appendHistory(nodes)
    }

    // Persist known node identities so they survive page refresh
    if (USE_REAL_MQTT && Object.keys(nodes).length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(nodes))
      } catch { /* quota exceeded or private browsing — silently skip */ }
    }
  }, [nodes, appendHistory])

  // ── FAILOVER SIMULATION (demo button) ─────────────────────────────────────
  const [failoverActive, setFailoverActive] = useState(false)

  const simulateFailover = useCallback(() => {
    if (failoverActive) return
    setFailoverActive(true)

    const steps = [
      [0,    'med',  'flat03: WiFi publish failed (attempt 1/3)...'],
      [600,  'med',  'flat03: WiFi publish failed (attempt 2/3)...'],
      [1200, 'med',  'flat03: WiFi publish failed (attempt 3/3) — switching to LoRa fallback'],
      [1800, 'high', 'flat03: FAILOVER ACTIVE — now transmitting via LoRaWAN'],
    ]
    steps.forEach(([delay, sev, msg]) => {
      setTimeout(() => {
        pushAlerts([{ sev, msg, time: new Date().toLocaleTimeString() }])
        if (sev === 'high') {
          setNodes(prev => ({ ...prev, flat03: { ...prev.flat03, mode: 'lora' } }))
        }
      }, delay)
    })
  }, [failoverActive, pushAlerts])

  const recoverNode = useCallback(() => {
    const steps = [
      [0,    'info', 'flat03: WiFi connection restored — testing...'],
      [400,  'info', 'flat03: WiFi success (1/3)'],
      [800,  'info', 'flat03: WiFi success (2/3)'],
      [1200, 'info', 'flat03: WiFi success (3/3) — switching back to WiFi mode'],
      [1600, 'info', 'flat03: RECOVERED — resumed WiFi primary mode'],
    ]
    steps.forEach(([delay, sev, msg]) => {
      setTimeout(() => {
        pushAlerts([{ sev, msg, time: new Date().toLocaleTimeString() }])
        if (delay === 1600) {
          setNodes(prev => ({ ...prev, flat03: { ...prev.flat03, mode: 'wifi' } }))
          setFailoverActive(false)
        }
      }, delay)
    })
  }, [pushAlerts])

  // ── WATCHDOG: Mark nodes offline if no heartbeat for 60s ───────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      // Read current node state via ref — avoids relying on updater side effects
      const newlyOffline = Object.keys(nodesRef.current).filter(id => {
        const node = nodesRef.current[id]
        const timeout = node.mode === 'lora' ? 120000 : 60000
        return node.online && node.lastSeen && (now - node.lastSeen > timeout)
      })

      if (!newlyOffline.length) return

      setNodes(prev => {
        const next = { ...prev }
        newlyOffline.forEach(id => {
          next[id] = { ...prev[id], online: false, mode: 'offline' }
        })
        return next
      })

      const time = new Date().toLocaleTimeString()
      pushAlerts(newlyOffline.map(id => ({
        sev: 'high',
        msg: `${id.toUpperCase()}: OFFLINE (no heartbeat > 60s)`,
        time,
      })))
    }, 10000) // Run check every 10 seconds

    return () => clearInterval(interval)
  }, [pushAlerts])

  const clearNodes = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setNodes({})
    setHistory({})
  }, [])

  return {
    nodes, history, alerts,
    failoverActive,
    simulateFailover,
    recoverNode,
    clearNodes,
    useMqtt: USE_REAL_MQTT,
  }
}
