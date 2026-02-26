import { NODE_IDS, NODE_COLORS, ANOMALY_NODE } from '../utils/simulator'

export default function NeighborGrid({ nodes }) {
  const temps  = NODE_IDS.map(id => nodes[id].temp)
  const mean   = temps.reduce((a, b) => a + b, 0) / temps.length
  const anomalyTemp = nodes[ANOMALY_NODE].temp
  const isAnomaly   = anomalyTemp > mean + 2.5

  return (
    <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:14, overflow:'hidden' }}>
      <div style={{
        padding:'14px 20px', borderBottom:'1px solid var(--border)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        fontSize:12, fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.05em', color:'var(--text-muted)',
      }}>
        <span>NEIGHBOR COMPARISON (°C)</span>
        {isAnomaly && (
          <span style={{ color:'var(--accent-alert)', fontSize:11 }}>⚠ ANOMALY DETECTED</span>
        )}
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:2, padding:'16px 20px' }}>
        {NODE_IDS.map(id => {
          const n       = nodes[id]
          const delta   = n.temp - mean
          const isAnom  = id === ANOMALY_NODE && isAnomaly
          const sign    = delta >= 0 ? '+' : ''
          const deltaColor = delta > 2 ? 'var(--accent-alert)' : 'var(--accent-ok)'

          return (
            <div key={id} style={{
              background: isAnom ? 'rgba(239,68,68,0.06)' : 'var(--surface2)',
              border: isAnom ? '1px solid rgba(239,68,68,0.4)' : '1px solid transparent',
              borderRadius:8, padding:'10px 12px', textAlign:'center',
            }}>
              <div style={{ fontFamily:'var(--mono)', fontSize:10, color:'var(--text-muted)', marginBottom:4 }}>
                {id.toUpperCase()}{isAnom ? ' ⚠' : ''}
              </div>
              <div style={{ fontFamily:'var(--mono)', fontSize:16, fontWeight:700, color:NODE_COLORS[id] }}>
                {n.temp.toFixed(1)}°
              </div>
              <div style={{ fontFamily:'var(--mono)', fontSize:10, marginTop:3, color:deltaColor }}>
                {sign}{delta.toFixed(1)} vs avg
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
