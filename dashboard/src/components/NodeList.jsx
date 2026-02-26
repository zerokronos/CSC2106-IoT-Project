import { useState } from 'react'
import { NODE_IDS } from '../utils/simulator'

const modeBadgeStyle = (mode) => {
  const map = {
    wifi:    { background:'rgba(0,212,255,0.12)',   color:'var(--accent-wifi)',  border:'1px solid rgba(0,212,255,0.2)' },
    lora:    { background:'rgba(249,115,22,0.12)',  color:'var(--accent-lora)',  border:'1px solid rgba(249,115,22,0.2)' },
    offline: { background:'rgba(100,116,139,0.12)', color:'var(--text-muted)',   border:'1px solid var(--border)' },
  }
  return {
    fontFamily:'var(--mono)', fontSize:10, fontWeight:700,
    padding:'2px 8px', borderRadius:4, letterSpacing:'0.06em',
    ...map[mode],
  }
}

const dotColor = (node) => {
  if (!node.online)      return { background:'var(--text-dim)' }
  if (node.alertActive)  return { background:'var(--accent-alert)', animation:'pulse-dot 0.8s ease-in-out infinite' }
  return { background:'var(--accent-ok)' }
}

const valColor = (val, warnThresh, alertThresh) => {
  if (val >= alertThresh) return 'var(--accent-alert)'
  if (val >= warnThresh)  return 'var(--accent-warn)'
  return 'var(--text)'
}

export default function NodeList({ nodes }) {
  const [selected, setSelected] = useState(null)

  return (
    <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:14, overflow:'hidden' }}>
      {/* header */}
      <div style={{
        padding:'14px 20px', borderBottom:'1px solid var(--border)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        fontSize:12, fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.05em', color:'var(--text-muted)',
      }}>
        <span>FLAT NODES</span>
        <span style={{ color:'var(--text)' }}>{NODE_IDS.length} nodes</span>
      </div>

      {NODE_IDS.map((id, i) => {
        const n    = nodes[id]
        const mode = n.online ? n.mode : 'offline'
        const isLast = i === NODE_IDS.length - 1
        const isSel  = selected === id

        return (
          <div
            key={id}
            onClick={() => setSelected(isSel ? null : id)}
            style={{
              padding:'14px 20px',
              borderBottom: isLast ? 'none' : '1px solid var(--border)',
              display:'flex', flexDirection:'column', gap:8,
              cursor:'pointer',
              background: isSel ? 'var(--surface2)' : 'transparent',
              transition:'background 0.15s',
              position:'relative',
            }}
          >
            {/* selected left bar */}
            {isSel && (
              <div style={{
                position:'absolute', left:0, top:0, bottom:0, width:3,
                background:'var(--accent-wifi)', borderRadius:'0 2px 2px 0',
              }} />
            )}

            {/* top row */}
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
              <div style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:13, display:'flex', alignItems:'center', gap:8 }}>
                <div style={{ width:8, height:8, borderRadius:'50%', ...dotColor(n) }} />
                {id.toUpperCase()}
              </div>
              <div style={modeBadgeStyle(mode)}>{mode.toUpperCase()}</div>
            </div>

            {/* readings */}
            <div style={{ display:'flex', gap:16 }}>
              {[
                { label:'TEMP',  val:`${n.temp.toFixed(1)}°C`,   color: valColor(n.temp,  35, 40) },
                { label:'SMOKE', val: n.smoke.toFixed(3),         color: valColor(n.smoke, 0.4, 0.7) },
                { label:'MODE',  val: mode,
                  color: mode==='wifi' ? 'var(--accent-wifi)' : mode==='lora' ? 'var(--accent-lora)' : 'var(--text-dim)' },
              ].map(r => (
                <div key={r.label} style={{ display:'flex', flexDirection:'column', gap:2 }}>
                  <div style={{ fontSize:10, color:'var(--text-muted)', fontFamily:'var(--mono)' }}>{r.label}</div>
                  <div style={{ fontFamily:'var(--mono)', fontSize:14, fontWeight:600, color:r.color }}>{r.val}</div>
                </div>
              ))}
            </div>

            <div style={{ fontSize:10, color:'var(--text-dim)', fontFamily:'var(--mono)' }}>
              Last seen: {n.online ? 'just now' : 'offline'}
            </div>
          </div>
        )
      })}
    </div>
  )
}
