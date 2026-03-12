import { NODE_COLORS } from '../utils/simulator'

export default function NeighborGrid({ nodes }) {
  const fallback = ['#00d4ff', '#22c55e', '#f97316', '#a78bfa', '#f472b6', '#facc15']
  const nodeIds = Object.keys(nodes).filter(id => nodes[id].online).sort()
  const temps = nodeIds.map(id => nodes[id].temp)
  const mean = temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : 0

  // Dynamic anomaly target: the hottest online node deviating from neighborhood mean.
  let anomalyNode = null
  let maxDelta = -Infinity
  nodeIds.forEach(id => {
    const delta = nodes[id].temp - mean
    if (delta > maxDelta) {
      maxDelta = delta
      anomalyNode = id
    }
  })
  const isAnomaly = nodeIds.length >= 2 && maxDelta > 2.5

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
        {nodeIds.length === 0 && (
          <div style={{ gridColumn:'1 / -1', textAlign:'center', fontFamily:'var(--mono)', fontSize:12, color:'var(--text-dim)', padding:'8px 0' }}>
            Waiting for online nodes...
          </div>
        )}

        {nodeIds.map((id, idx) => {
          const n       = nodes[id]
          const delta   = n.temp - mean
          const isAnom  = id === anomalyNode && isAnomaly
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
              <div style={{ fontFamily:'var(--mono)', fontSize:16, fontWeight:700, color:NODE_COLORS[id] ?? fallback[idx % fallback.length] }}>
                {(n.temp ?? 0).toFixed(1)}°
              </div>
              <div style={{ fontFamily:'var(--mono)', fontSize:10, marginTop:3, color:deltaColor }}>
                {sign}{(delta ?? 0).toFixed(1)} vs avg
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
