import { useState, useEffect, useRef, useCallback } from 'react'
import {
  NODE_IDS, makeInitialNodes, simulateTick, normalise,
  TEMP_ALARM, SMOKE_ALARM,
} from '../utils/simulator'

// ─── TOGGLE THIS when the real broker is ready ───────────────────────────────
const USE_REAL_MQTT   = false
const MQTT_BROKER_URL = 'ws://192.168.1.x:9001'   // <- set broker IP here
// ─────────────────────────────────────────────────────────────────────────────

const MAX_HISTORY = 60
const MAX_ALERTS  = 30

export function useDashboard() {
  const [nodes,   setNodes]   = useState(makeInitialNodes)
  const [history, setHistory] = useState(() => {
    const h = {}
    NODE_IDS.forEach(id => { h[id] = [] })
    return h
  })
  const [alerts,  setAlerts]  = useState([])
  const tickRef   = useRef(0)
  const mqttRef   = useRef(null)

  // ── push alert helper ──────────────────────────────────────────────────────
  const pushAlerts = useCallback((incoming) => {
    if (!incoming.length) return
    setAlerts(prev => [...incoming, ...prev].slice(0, MAX_ALERTS))
  }, [])

  // ── append history helper ──────────────────────────────────────────────────
  const appendHistory = useCallback((updatedNodes) => {
    setHistory(prev => {
      const next = { ...prev }
      NODE_IDS.forEach(id => {
        const n = updatedNodes[id]
        if (!n.online) return
        next[id] = [
          ...prev[id],
          { t: tickRef.current, temp: n.temp, smoke: n.smoke },
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
        appendHistory(next)
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
    import('mqtt').then(({ connect }) => {
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

          if (topic.startsWith('telemetry/')) {
            setNodes(prev => {
              const n = { ...prev[data.id], ...data, lastSeen: Date.now() }
              n.alertActive = n.temp > TEMP_ALARM || n.smoke > SMOKE_ALARM
              appendHistory({ ...prev, [data.id]: n })
              return { ...prev, [data.id]: n }
            })
          }

          if (topic.startsWith('alert/')) {
            pushAlerts([{
              sev:  raw.severity ?? 'med',
              msg:  raw.msg      ?? `Alert from ${data.id}`,
              time: new Date().toLocaleTimeString(),
            }])
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
  }, [appendHistory, pushAlerts])

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

  return {
    nodes, history, alerts,
    failoverActive,
    simulateFailover,
    recoverNode,
    useMqtt: USE_REAL_MQTT,
  }
}
