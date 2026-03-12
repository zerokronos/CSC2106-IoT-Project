const modeColors = {
  wifi:    { bg:'rgba(0,212,255,0.1)',  color:'var(--accent-wifi)',  border:'rgba(0,212,255,0.2)'  },
  lora:    { bg:'rgba(249,115,22,0.1)', color:'var(--accent-lora)',  border:'rgba(249,115,22,0.2)' },
  offline: { bg:'rgba(100,116,139,0.1)',color:'var(--text-muted)',   border:'var(--border)'        },
}
const modeIcon = { wifi:'📶', lora:'📡', offline:'✕' }

export default function FailoverBar({ nodes, failoverActive, onSimulate, onRecover }) {
  const nodeIds = Object.keys(nodes).sort()

  return (
    <div style={{
      background:'var(--surface)', border:'1px solid var(--border)',
      borderRadius:14, padding:'16px 20px',
      display:'flex', alignItems:'center', gap:20, flexWrap:'wrap',
    }}>
      <div style={{ fontFamily:'var(--mono)', fontSize:11, color:'var(--text-muted)', letterSpacing:'0.06em', flexShrink:0 }}>
        NODE MODES
      </div>

      <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
        {nodeIds.length === 0 && (
          <div style={{ fontFamily:'var(--mono)', fontSize:11, color:'var(--text-dim)' }}>
            No connected nodes
          </div>
        )}

        {nodeIds.map(id => {
          const n = nodes[id]
          if (!n) return null
          const mode = n.online ? (n.mode || 'wifi') : 'offline'
          const c = modeColors[mode] || modeColors.offline
          return (
            <div key={id} style={{
              fontFamily:'var(--mono)', fontSize:11, fontWeight:700,
              padding:'4px 10px', borderRadius:20,
              background: c.bg, color: c.color, border:`1px solid ${c.border}`,
              display:'flex', alignItems:'center', gap:6,
            }}>
              <span style={{ width:5, height:5, borderRadius:'50%', background:'currentColor', display:'inline-block' }} />
              {modeIcon[mode]} {id}
            </div>
          )
        })}
      </div>

      <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
        <button
          onClick={onSimulate}
          disabled={failoverActive}
          style={{
            fontFamily:'var(--mono)', fontSize:11, fontWeight:700,
            padding:'8px 16px', borderRadius:8, border:'none', cursor: failoverActive ? 'default' : 'pointer',
            letterSpacing:'0.06em',
            background: failoverActive ? 'var(--accent-alert)' : 'rgba(239,68,68,0.15)',
            color: failoverActive ? 'white' : 'var(--accent-alert)',
            outline: '1px solid rgba(239,68,68,0.3)',
            transition:'all 0.2s',
          }}
        >
          ⚠ SIMULATE WiFi FAIL (flat03)
        </button>

        {failoverActive && (
          <button
            onClick={onRecover}
            style={{
              fontFamily:'var(--mono)', fontSize:11, fontWeight:700,
              padding:'8px 16px', borderRadius:8, border:'none', cursor:'pointer',
              letterSpacing:'0.06em',
              background:'rgba(34,197,94,0.12)', color:'var(--accent-ok)',
              outline:'1px solid rgba(34,197,94,0.25)',
            }}
          >
            ↩ RESTORE WiFi
          </button>
        )}
      </div>
    </div>
  )
}
