import { useDashboard } from './hooks/useDashboard'
import Header       from './components/Header'
import StatStrip    from './components/StatStrip'
import FailoverBar  from './components/FailoverBar'
import NodeList     from './components/NodeList'
import TempChart    from './components/TempChart'
import NeighborGrid from './components/NeighborGrid'
import AlertsFeed   from './components/AlertsFeed'

export default function App() {
  const {
    nodes, history, alerts,
    failoverActive, simulateFailover, recoverNode,
    useMqtt,
  } = useDashboard()

  return (
    <div>
      <Header useMqtt={useMqtt} />

      <main style={{
        padding:'24px 28px',
        maxWidth:1400,
        margin:'0 auto',
        display:'grid',
        gap:20,
      }}>

        <StatStrip nodes={nodes} />

        <FailoverBar
          nodes={nodes}
          failoverActive={failoverActive}
          onSimulate={simulateFailover}
          onRecover={recoverNode}
        />

        {/* main two-column grid */}
        <div style={{ display:'grid', gridTemplateColumns:'380px 1fr', gap:20, alignItems:'start' }}>

          <NodeList nodes={nodes} />

          <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <TempChart    history={history} />
            <NeighborGrid nodes={nodes} />
            <AlertsFeed   alerts={alerts} />
          </div>

        </div>
      </main>
    </div>
  )
}
