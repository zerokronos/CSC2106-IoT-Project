import { NODE_IDS } from '../utils/simulator'

const card = (accentColor) => ({
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: '16px 20px',
  position: 'relative',
  overflow: 'hidden',
  '--accent-color': accentColor,
})

const topBar = { position:'absolute', top:0, left:0, right:0, height:2, background:'var(--accent-color)' }
const label  = { fontSize:11, color:'var(--text-muted)', fontFamily:'var(--mono)', letterSpacing:'0.06em', marginBottom:8 }
const sub    = { fontSize:11, color:'var(--text-muted)', marginTop:4 }

export default function StatStrip({ nodes }) {
  const online = NODE_IDS.filter(id => nodes[id].online)
  const wifi   = online.filter(id => nodes[id].mode === 'wifi')
  const lora   = online.filter(id => nodes[id].mode === 'lora')
  const alerted= NODE_IDS.filter(id => nodes[id].alertActive)

  const stats = [
    { label:'NODES ONLINE',  value: online.length,  sub:'of 6 total nodes',       color:'var(--accent-ok)',    textColor:'var(--accent-ok)' },
    { label:'WiFi MODE',     value: wifi.length,    sub:'primary comms active',    color:'var(--accent-wifi)',  textColor:'var(--accent-wifi)' },
    { label:'LoRa FALLBACK', value: lora.length,    sub:'nodes in fallback mode',  color:'var(--accent-lora)',  textColor:'var(--accent-lora)' },
    { label:'ACTIVE ALERTS', value: alerted.length, sub:'threshold breaches',      color:'var(--accent-alert)', textColor:'var(--accent-alert)' },
  ]

  return (
    <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12 }}>
      {stats.map(s => (
        <div key={s.label} style={card(s.color)}>
          <div style={topBar} />
          <div style={label}>{s.label}</div>
          <div style={{ fontFamily:'var(--mono)', fontSize:28, fontWeight:700, color:s.textColor }}>{s.value}</div>
          <div style={sub}>{s.sub}</div>
        </div>
      ))}
    </div>
  )
}
