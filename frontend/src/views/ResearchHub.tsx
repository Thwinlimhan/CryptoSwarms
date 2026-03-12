import { Search, Shield, Activity, Zap } from 'lucide-react';
import { useState, useEffect } from 'react';

interface ResearchData {
  regime: string;
  detected_patterns: string[];
  whale_trades: { type: string, size: string, value: string, time: string }[];
  funding_rates: { symbol: string, rate: string, opportunity: string }[];
  guardian_status: { system: string, warnings: number, leaks: number, last_scan: string, scan_count?: number };
  hot_assets: { symbol: string, price: string, change: string, volume_24h?: number }[];
}

export default function ResearchHub() {
  const [data, setData] = useState<ResearchData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/research/latest');
        const json = await res.json();
        setData(json);
      } catch (e) {
        console.error("Failed to fetch research data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="loading-container">INITIALIZING_SEARCH_SWARM...</div>;
  if (!data) return <div className="error-container">RESEARCH_API_UNREACHABLE</div>;

  return (
    <div className="view-container">
      <header className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Search className="text-primary" size={24} />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', letterSpacing: '0.1em' }}>RESEARCH_HUB</h1>
            <div className="text-muted" style={{ fontSize: '0.8rem' }}>SWARM_INTELLIGENCE // REAL-TIME_DISCOVERY</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div className="status-tag active">SWARM_ONLINE</div>
          <div className="status-tag">AGENTS: 124</div>
        </div>
      </header>

      <div className="grid grid-cols-4" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-label">MARKET_REGIME</div>
          <div className="stat-value text-info" style={{ fontSize: '1.2rem' }}>{data.regime}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">WHALE_VOLUME_24H</div>
          <div className="stat-value">$1.48B</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">SIGNALS_GEN</div>
          <div className="stat-value text-primary">42</div>
        </div>
        <div className="stat-card" style={{ borderColor: 'var(--accent-alert)' }}>
          <div className="stat-label">RISK_LEVEL</div>
          <div className="stat-value text-danger">MEDIUM</div>
        </div>
      </div>

      <div className="grid grid-cols-3">
        {/* Left Column: Whale & Assets */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="border-box">
            <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', color: 'var(--accent-info)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={18} /> AGENT_DISCOVERIES
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {data.detected_patterns.map((p, i) => (
                <span key={i} style={{ 
                  background: 'rgba(0,255,65,0.05)', 
                  border: '1px solid var(--accent-info)', 
                  padding: '0.2rem 0.5rem', 
                  fontSize: '0.7rem',
                  borderRadius: '2px'
                }}>
                  {p}
                </span>
              ))}
            </div>
          </div>

          <div className="border-box">
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>WHALE_TRADE_TRACES</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              {data.whale_trades.map((w, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ color: w.type === 'BUY' ? 'var(--text-primary)' : '#ff3b3b' }}>{w.type} {w.size}</span>
                  <span style={{ opacity: 0.8 }}>{w.value}</span>
                  <span className="text-muted" style={{ fontSize: '0.7rem' }}>{w.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center Column: Funding & Market Inefficiencies */}
        <div className="border-box">
          <h3 style={{ margin: '0 0 1.5rem', fontSize: '1rem', color: 'var(--accent-info)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
             <Activity size={18} /> FUNDING_INEFFICIENCIES
          </h3>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>RATE</th>
                <th>OPPORTUNITY</th>
              </tr>
            </thead>
            <tbody>
              {data.funding_rates.map((f, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 'bold' }}>{f.symbol}</td>
                  <td style={{ color: '#ff3b3b' }}>{f.rate}</td>
                  <td>
                    <span style={{ 
                      color: f.opportunity === 'HIGH' ? 'var(--text-primary)' : '#ffb800',
                      fontSize: '0.7rem'
                    }}>{f.opportunity}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="blink" style={{ marginTop: '2rem', fontSize: '0.7rem', color: 'var(--accent-info)' }}>
            SCALPING_POSSIBILITIES_DETECTED_IN_PERP_LAYER...
          </div>
        </div>

        {/* Right Column: Guardian & System Health */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="border-box" style={{ borderLeft: '4px solid var(--accent-alert)' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', color: 'var(--accent-alert)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={18} /> GUARDIAN_OVERWATCH
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
               <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                 <div className="pulse" style={{ width: 10, height: 10, background: 'var(--text-primary)', borderRadius: '50%' }}></div>
                 <span>SYSTEM_INTEGRITY: {data.guardian_status.system}</span>
               </div>
               <div style={{ fontSize: '0.8rem', paddingLeft: '1.25rem', borderLeft: '1px solid #333' }}>
                 <div className="text-secondary">• {data.guardian_status.warnings} ACTIVE_WARNINGS</div>
                 <div style={{ color: 'var(--accent-alert)' }}>• {data.guardian_status.leaks} MEMORY_FRAGMENTATION</div>
                 <div className="text-muted" style={{ marginTop: '0.5rem', fontSize: '0.7rem' }}>LAST_SCAN: {data.guardian_status.last_scan}</div>
               </div>
            </div>
          </div>

          <div className="border-box">
             <h3 style={{ margin: '0 0 1rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>HOT_FLOWS</h3>
             <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
               {data.hot_assets.map((a, i) => (
                 <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{a.symbol}</span>
                      <span className="text-muted" style={{ fontSize: '0.7rem' }}>{a.price}</span>
                    </div>
                    <span style={{ color: a.change.startsWith('+') ? 'var(--text-primary)' : '#ff3b3b', fontSize: '0.8rem' }}>{a.change}</span>
                 </div>
               ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
