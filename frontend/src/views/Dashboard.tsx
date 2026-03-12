import { ShieldAlert, Cpu, Play, Square, RefreshCw, Zap, TrendingUp } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface AgentStatus {
  status: string;
  since: string | null;
  signals_today: number;
  last_heartbeat: string | null;
}

interface ReadinessCheck {
  redis: boolean;
  timescaledb: boolean;
  neo4j: boolean;
  qdrant: boolean;
  sglang: boolean;
}

interface OverviewData {
  time: string;
  readiness: {
    ok: boolean;
    checks: ReadinessCheck;
  };
  agent_status: Record<string, AgentStatus>;
  healthy_agent_count: number;
  total_agent_count: number;
  signals_today: number;
  dag_memory: {
    node_count: number;
    edge_count: number;
    topic_count: number;
    topic_entropy: number;
    recall_hit_rate: number;
    research_hypothesis_count: number;
    decision_checkpoint_count: number;
    top_topics: any[];
  }
}

interface RegimeData {
  regime: string;
  confidence: number;
}

interface RunnerStatus {
  running: boolean;
  scan_count: number;
  last_regime: string;
  signal_count: number;
  latest_signals: { signal_type: string; symbol: string; confidence: number; priority: string; source: string }[];
  funding_pairs_tracked: number;
  hot_assets: { symbol: string; price: string; change: string; volume_24h?: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [runner, setRunner] = useState<RunnerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [swarmStatus, setSwarmStatus] = useState<'idle' | 'starting' | 'running' | 'stopping'>('idle');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [overviewRes, regimeRes, runnerRes] = await Promise.all([
          fetch(`${API_URL}/api/dashboard/overview`),
          fetch(`${API_URL}/api/regime/current`),
          fetch(`${API_URL}/api/agents/runner-status`),
        ]);
        const overviewData = await overviewRes.json();
        const regimeData = await regimeRes.json();
        const runnerData = await runnerRes.json();
        setData(overviewData);
        setRegime(regimeData);
        setRunner(runnerData);
        if (runnerData?.running) setSwarmStatus('running');
      } catch (e) {
        console.error("Failed to fetch dashboard data:", e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const controlSwarm = async (action: 'start' | 'stop') => {
    setSwarmStatus(action === 'start' ? 'starting' : 'stopping');
    try {
      const res = await fetch(`${API_URL}/api/agents/control?action=${action}`, { method: 'POST' });
      const result = await res.json();
      if (result.status === 'SUCCESS') {
        setSwarmStatus(action === 'start' ? 'running' : 'idle');
      }
    } catch (e) {
      console.error("Swarm control failure:", e);
      setSwarmStatus('idle');
    }
  };

  if (loading || !data || !regime) {
    return (
       <div>
         <h2 style={{ marginBottom: "2rem" }}><Cpu size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> SWARM_OVERVIEW</h2>
         <div className="blink">_CONNECTING TO SWARM...</div>
       </div>
    );
  }

  const { dag_memory, readiness, agent_status } = data;

  return (
    <div>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ margin: 0 }}><Cpu size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> SWARM_OVERVIEW</h2>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {runner?.running && (
            <span style={{
              background: 'rgba(0,255,65,0.1)',
              border: '1px solid rgba(0,255,65,0.4)',
              padding: '0.3rem 0.8rem',
              fontSize: '0.7rem',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-primary)',
              animation: 'pulse 2s infinite',
            }}>
              ● LIVE — {runner.scan_count} SCANS
            </span>
          )}
          {swarmStatus === 'running' || runner?.running ? (
            <button 
              onClick={() => controlSwarm('stop')}
              style={{ borderColor: 'var(--accent-alert)', color: 'var(--accent-alert)', background: 'rgba(255,0,60,0.05)' }}
            >
              <Square size={14} style={{ marginRight: '0.5rem' }}/> TERMINATE_SWARM
            </button>
          ) : (
            <button 
              onClick={() => controlSwarm('start')}
              disabled={swarmStatus === 'starting'}
            >
              {swarmStatus === 'starting' ? (
                <RefreshCw size={14} className="spin" style={{ marginRight: '0.5rem' }}/>
              ) : (
                <Play size={14} style={{ marginRight: '0.5rem' }}/>
              )}
              {swarmStatus === 'starting' ? 'INITIALIZING...' : 'DEPLOY_PRODUCTION_SWARM'}
            </button>
          )}
        </div>
      </header>
      
      <div className="grid grid-cols-4">
        <div className="stat-card" style={{ borderColor: runner?.running ? 'var(--accent-info)' : 'var(--accent-alert)' }}>
          <div className="stat-label">SCANNER_STATUS</div>
          <div className="stat-value" style={{ color: runner?.running ? 'var(--text-primary)' : 'var(--accent-alert)', fontSize: '1.1rem' }}>
            {runner?.running ? 'SCANNING' : 'OFFLINE'}
          </div>
          <div className="text-muted" style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>
            {runner?.signal_count || 0} signals found
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">SIGNALS_TODAY</div>
          <div className="stat-value text-info">{data.signals_today}</div>
          <div className="text-muted" style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>
            from {data.total_agent_count} agents
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">MARKET_REGIME</div>
          <div className="stat-value text-warn" style={{ fontSize: '1.1rem' }}>{(runner?.last_regime || regime.regime).toUpperCase()}</div>
          <div className="text-muted" style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>
            confidence: {(regime.confidence * 100).toFixed(0)}%
          </div>
        </div>
        <div className="stat-card" style={{ padding: '1rem', borderColor: 'var(--accent-gold)' }}>
           <div className="stat-label">DAG_ENTROPY / RECALL</div>
           <div style={{ fontSize: '1.2rem' }} className="text-gold">
             {dag_memory.topic_entropy.toFixed(2)} / {(dag_memory.recall_hit_rate * 100).toFixed(1)}%
           </div>
        </div>
      </div>

      <div className="grid grid-cols-2">
        {/* Live Signal Feed from Agents */}
        <div className="border-box" style={{ height: "400px", overflowY: 'auto' }}>
           <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--accent-cyan)', paddingBottom: '0.5rem' }}>
             <Zap size={18} className="text-cyan" style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
             LIVE_SIGNAL_FEED
             {runner?.running && <span className="blink" style={{ marginLeft: '0.5rem', color: 'var(--text-primary)', fontSize: '0.7rem' }}>● ACTIVE</span>}
           </h3>
           <div className="feed-list">
             {runner?.latest_signals && runner.latest_signals.length > 0 ? (
               runner.latest_signals.map((sig, idx) => (
                 <div key={idx} className="feed-item" style={{ animation: 'fadeIn 0.3s ease-out' }}>
                   <span style={{
                     color: sig.priority === 'HIGH' ? 'var(--text-primary)' : '#ffb800',
                     fontWeight: 'bold',
                     fontSize: '0.75rem',
                     marginRight: '0.5rem',
                   }}>
                     {sig.signal_type}
                   </span>
                   <span className="feed-agent">{sig.symbol}</span>
                   <span className="text-muted" style={{ fontSize: '0.7rem' }}>
                     | conf: {(sig.confidence * 100).toFixed(0)}% | {sig.source}
                   </span>
                 </div>
               ))
             ) : (
               <>
                 {Object.entries(agent_status).map(([agent, status], idx) => (
                   <div key={idx} className="feed-item" style={{ animation: 'fadeIn 0.3s ease-out' }}>
                     <span className="feed-agent">{agent}</span>
                     <span style={{ color: status.status === 'healthy' ? 'var(--text-primary)' : 'var(--accent-alert)' }}>
                       {status.status.toUpperCase()}
                     </span>
                     <span className="text-muted">| Signals: {status.signals_today}</span>
                   </div>
                 ))}
               </>
             )}
             <div className="feed-item blink" style={{ borderLeft: 'none' }}>_</div>
           </div>
        </div>

        {/* Health, Assets, and Runner Status */}
        <div className="border-box" style={{ height: "400px", overflowY: 'auto' }}>
           <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--text-secondary)', paddingBottom: '0.5rem' }}>
             <ShieldAlert size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
             SYSTEM_HEALTH
           </h3>
           
           <table className="terminal-table">
             <thead>
               <tr>
                 <th>SUBSYSTEM</th>
                 <th>STATUS</th>
               </tr>
             </thead>
             <tbody>
               <tr>
                 <td>AgentRunner</td>
                 <td className={runner?.running ? "text-primary" : "text-danger"}>
                   {runner?.running ? `RUNNING (${runner.scan_count} scans)` : "STOPPED"}
                 </td>
               </tr>
               <tr>
                 <td>TimescaleDB</td>
                 <td className={readiness.checks.timescaledb ? "text-primary" : "text-danger"}>
                   {readiness.checks.timescaledb ? "OK" : "OFFLINE"}
                 </td>
               </tr>
               <tr>
                 <td>RedisHeartbeats</td>
                 <td className={readiness.checks.redis ? "text-primary" : "text-danger"}>
                   {readiness.checks.redis ? "OK" : "OFFLINE"}
                 </td>
               </tr>
               <tr>
                 <td>QdrantVectorStore</td>
                 <td className={readiness.checks.qdrant ? "text-primary" : "text-danger"}>
                   {readiness.checks.qdrant ? "OK" : "OFFLINE"}
                 </td>
               </tr>
               <tr>
                 <td>Neo4jGraph</td>
                 <td className={readiness.checks.neo4j ? "text-primary" : "text-danger"}>
                   {readiness.checks.neo4j ? "OK" : "OFFLINE"}
                 </td>
               </tr>
               <tr>
                 <td>SGLangLLM</td>
                 <td className={readiness.checks.sglang ? "text-primary" : "text-danger"}>
                   {readiness.checks.sglang ? "OK" : "OFFLINE"}
                 </td>
               </tr>
             </tbody>
           </table>

           {/* Hot Assets from Live Binance Data */}
           {runner?.hot_assets && runner.hot_assets.length > 0 && (
             <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.75rem' }}>
               <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                 <TrendingUp size={14} /> LIVE_BINANCE_PRICES
               </h4>
               {runner.hot_assets.map((asset, i) => (
                 <div key={i} style={{
                   display: 'flex',
                   justifyContent: 'space-between',
                   padding: '0.3rem 0',
                   fontSize: '0.8rem',
                   fontFamily: 'var(--font-mono)',
                   borderBottom: '1px solid rgba(255,255,255,0.04)',
                 }}>
                   <span style={{ fontWeight: 'bold' }}>{asset.symbol}</span>
                   <span>{asset.price}</span>
                   <span style={{
                     color: asset.change?.startsWith('+') ? 'var(--text-primary)' : '#ff3b3b',
                   }}>{asset.change}</span>
                 </div>
               ))}
             </div>
           )}
        </div>
      </div>
    </div>
  );
}
