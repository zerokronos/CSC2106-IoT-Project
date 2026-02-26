const sevStyle = {
  high: { background:'var(--accent-alert)', boxShadow:'0 0 6px var(--accent-alert)' },
  med:  { background:'var(--accent-warn)' },
  info: { background:'var(--accent-wifi)' },
}

export default function AlertsFeed({ alerts }) {
  return (
    <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:14, overflow:'hidden' }}>
      <div style={{
        padding:'14px 20px', borderBottom:'1px solid var(--border)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        fontSize:12, fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.05em', color:'var(--text-muted)',
      }}>
        <span>ALERTS FEED</span>
        <span style={{ color:'var(--text)' }}>{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
      </div>

      <div style={{ maxHeight:200, overflowY:'auto' }}>
        {alerts.length === 0 ? (
          <div style={{ padding:20, textAlign:'center', color:'var(--text-dim)', fontFamily:'var(--mono)', fontSize:12 }}>
            No alerts — all systems nominal
          </div>
        ) : alerts.slice(0, 15).map((a, i) => (
          <div
            key={i}
            style={{
              padding:'10px 20px',
              borderBottom: i < Math.min(alerts.length, 15) - 1 ? '1px solid var(--border)' : 'none',
              display:'flex', alignItems:'flex-start', gap:12,
              animation:'slideIn 0.3s ease',
            }}
          >
            <div style={{
              width:6, height:6, borderRadius:'50%',
              flexShrink:0, marginTop:6,
              ...sevStyle[a.sev],
            }} />
            <div style={{ flex:1 }}>
              <div style={{ fontSize:12, fontFamily:'var(--mono)' }}>{a.msg}</div>
              <div style={{ fontSize:10, color:'var(--text-muted)', fontFamily:'var(--mono)', marginTop:2 }}>{a.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
