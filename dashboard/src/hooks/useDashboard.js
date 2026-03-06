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

export function useDashboard() {
  const [nodes,   setNodes]   = useState(() => (USE_REAL_MQTT ? {} : makeInitialNodes()))
  const [history, setHistory] = useState(() => (USE_REAL_MQTT ? {} : Object.fromEntries(NODE_IDS.map(id => [id, []]))))
  const [alerts,  setAlerts]  = useState([])
  const tickRef   = useRef(0)
  const mqttRef   = useRef(null)

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
        client.subscribe('telemetry/#')
        client.subscribe('alert/#')
        client.subscribe('heartbeat/#')
      })

      client.on('message', (topic, payload) => {
        try {
          const raw  = JSON.parse(payload.toString())
          const data = normalise(raw)
          const topicId = topic.split('/').filter(Boolean).pop()
          const id = data.id ?? topicId
          if (!id) return

          if (topic.startsWith('telemetry/')) {
            setNodes(prev => {
              try {
                const existing = prev[id] ?? makeNode(id)
                const nextNode = {
                  ...existing,
                  ...data,
                  online: true,
                  mode: data.mode ?? (existing.mode === 'offline' ? 'wifi' : (existing.mode ?? 'wifi')),
                  lastSeen: Date.now(),
                  fireDetected: Boolean(data.fireDetected),
                }

                // Independent breach detection
                const tempVal = Number(nextNode.temp ?? 0)
                const smokeVal = Number(nextNode.smoke ?? 0)
                
                const isTempAlert  = tempVal > TEMP_ALARM
                const isSmokeAlert = smokeVal > SMOKE_ALARM
                const isFireAlert  = nextNode.fireDetected

                const wasTempAlert  = Number(existing.temp ?? 0) > TEMP_ALARM
                const wasSmokeAlert = Number(existing.smoke ?? 0) > SMOKE_ALARM
                const wasFireAlert  = existing.fireDetected

                const wasAlert = existing.alertActive
                nextNode.alertActive = isTempAlert || isSmokeAlert || isFireAlert

                // Trigger alert if ANY threshold is newly crossed
                if ((isTempAlert && !wasTempAlert) || (isSmokeAlert && !wasSmokeAlert) || (isFireAlert && !wasFireAlert)) {
                  let cause = []
                  if (isTempAlert && !wasTempAlert)   cause.push(`HIGH TEMP (${tempVal.toFixed(1)}°C)`)
                  if (isSmokeAlert && !wasSmokeAlert) cause.push(`HIGH SMOKE (${smokeVal.toFixed(1)} PPM)`)
                  if (isFireAlert && !wasFireAlert)   cause.push('FIRE DETECTED')

                  const displayId = String(id).toUpperCase()
                  pushAlerts([{
                    sev: 'high',
                    msg: `${displayId} FLAGGED: ${cause.join(' & ')}`,
                    time: new Date().toLocaleTimeString(),
                  }])
                }

                // Recovery detection
                if (wasAlert && !nextNode.alertActive) {
                  pushAlerts([{
                    sev: 'info',
                    msg: `${String(id).toUpperCase()}: RECOVERED — All thresholds nominal`,
                    time: new Date().toLocaleTimeString(),
                  }])
                }

                return { ...prev, [id]: nextNode }
              } catch (err) {
                console.error("Critical error updating node state:", err)
                return prev
              }
            })
          }

          if (topic.startsWith('alert/')) {
            pushAlerts([{
              sev:  raw.severity ?? 'med',
              msg:  raw.msg      ?? `Alert from ${data.id}`,
              time: new Date().toLocaleTimeString(),
            }])
          }

          if (topic.startsWith('heartbeat/')) {
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

  // ── EFFECT for HISTORY ─────────────────────────────────────────────────────
  const isInitialMount = useRef(true)
  useEffect(() => {
    // Skip the initial render to prevent duplicate history on mount
    if (isInitialMount.current) {
      isInitialMount.current = false
    } else {
      appendHistory(nodes)
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
      const newlyOffline = []
      setNodes(prev => {
        const now = Date.now()
        let changed = false
        const next = { ...prev }

        Object.keys(next).forEach(id => {
          const node = next[id]
          // If online and hasn't been seen in 60s (2 missed heartbeats)
          if (node.online && node.lastSeen && (now - node.lastSeen > 60000)) {
            next[id] = { ...node, online: false, mode: 'offline' }
            newlyOffline.push(id)
            changed = true
          }
        })
        return changed ? next : prev
      })

      if (newlyOffline.length) {
        const time = new Date().toLocaleTimeString()
        pushAlerts(newlyOffline.map(id => ({
          sev: 'med',
          msg: `${id.toUpperCase()}: OFFLINE (no heartbeat > 60s)`,
          time,
        })))
      }
    }, 10000) // Run check every 10 seconds

    return () => clearInterval(interval)
  }, [pushAlerts])

  return {
    nodes, history, alerts,
    failoverActive,
    simulateFailover,
    recoverNode,
    useMqtt: USE_REAL_MQTT,
  }
}
