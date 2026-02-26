import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  ReferenceLine, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { NODE_IDS, NODE_COLORS, ANOMALY_NODE } from '../utils/simulator'

// Merge per-node history arrays into one array of { t, flat01, flat02, ... }
function mergeHistory(history) {
  const len = Math.max(...NODE_IDS.map(id => history[id].length))
  return Array.from({ length: len }, (_, i) => {
    const point = { i }
    NODE_IDS.forEach(id => {
      const h = history[id]
      const offset = h.length - len
      const entry  = h[i + offset]
      if (entry) point[id] = parseFloat(entry.temp.toFixed(2))
    })
    return point
  })
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background:'var(--surface2)', border:'1px solid var(--border)',
      borderRadius:8, padding:'8px 12px', fontSize:11, fontFamily:'var(--mono)',
    }}>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom:2 }}>
          {p.dataKey}: {p.value}°C
        </div>
      ))}
    </div>
  )
}

export default function TempChart({ history }) {
  const data = mergeHistory(history)

  return (
    <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:14, overflow:'hidden' }}>
      <div style={{
        padding:'14px 20px', borderBottom:'1px solid var(--border)',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        fontSize:12, fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.05em', color:'var(--text-muted)',
      }}>
        <span>TEMPERATURE TREND — ALL NODES (°C)</span>
        <span style={{ color:'var(--text-muted)' }}>last 60s</span>
      </div>

      <div style={{ padding:'20px 20px 10px' }}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top:5, right:10, left:0, bottom:5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,47,74,0.8)" />
            <XAxis dataKey="i" hide />
            <YAxis
              domain={[18, 50]}
              tick={{ fontFamily:'var(--mono)', fontSize:10, fill:'rgba(100,116,139,0.8)' }}
              tickLine={false}
              axisLine={false}
              width={30}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={40}
              stroke="rgba(239,68,68,0.5)"
              strokeDasharray="4 4"
              label={{ value:'ALARM 40°C', fill:'rgba(239,68,68,0.7)', fontSize:9, fontFamily:'var(--mono)' }}
            />
            {NODE_IDS.map(id => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                stroke={NODE_COLORS[id]}
                strokeWidth={id === ANOMALY_NODE ? 2.5 : 1.5}
                dot={false}
                strokeOpacity={id === ANOMALY_NODE ? 1 : 0.65}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div style={{ display:'flex', gap:16, flexWrap:'wrap', marginTop:8, paddingLeft:30 }}>
          {NODE_IDS.map(id => (
            <div key={id} style={{ display:'flex', alignItems:'center', gap:5 }}>
              <div style={{ width:10, height:3, background:NODE_COLORS[id], borderRadius:2 }} />
              <span style={{ fontFamily:'var(--mono)', fontSize:10, color:'rgba(148,163,184,0.8)' }}>{id}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
