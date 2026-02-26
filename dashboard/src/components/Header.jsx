import { useState, useEffect } from 'react'

const styles = {
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 28px',
    borderBottom: '1px solid var(--border)',
    background: 'rgba(10,15,26,0.95)',
    backdropFilter: 'blur(10px)',
    position: 'sticky', top: 0, zIndex: 100,
  },
  logo: { display: 'flex', alignItems: 'center', gap: 12 },
  logoIcon: {
    width: 36, height: 36,
    background: 'linear-gradient(135deg, var(--accent-wifi), #0077aa)',
    borderRadius: 8,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 18,
  },
  logoText: { fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 700, letterSpacing: '0.05em' },
  logoSub:  { fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: 2 },
  right:    { display: 'flex', alignItems: 'center', gap: 20 },
  liveBadge:{
    display: 'flex', alignItems: 'center', gap: 6,
    fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 600,
    color: 'var(--accent-ok)', letterSpacing: '0.08em',
  },
  liveDot: {
    width: 7, height: 7, borderRadius: '50%',
    background: 'var(--accent-ok)',
    animation: 'pulse-dot 1.4s ease-in-out infinite',
  },
  clock: { fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-muted)' },
  mqttTag: {
    fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
    padding: '2px 8px', borderRadius: 4,
    background: 'rgba(0,212,255,0.1)', color: 'var(--accent-wifi)',
    border: '1px solid rgba(0,212,255,0.2)', letterSpacing: '0.06em',
  },
}

export default function Header({ useMqtt }) {
  const [time, setTime] = useState(new Date().toLocaleTimeString())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <div style={styles.logoIcon}>🏢</div>
        <div>
          <div style={styles.logoText}>HDB IOT MONITOR</div>
          <div style={styles.logoSub}>CSC2106 · Team 6 · Multi-Protocol Network</div>
        </div>
      </div>
      <div style={styles.right}>
        {useMqtt && <div style={styles.mqttTag}>MQTT LIVE</div>}
        <div style={styles.liveBadge}>
          <div style={styles.liveDot} />
          LIVE
        </div>
        <div style={styles.clock}>{time}</div>
      </div>
    </header>
  )
}
