import { GitBranch, Target, Layers, Zap } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface Trace {
  time: string;
  strategy_id: string;
  action: string;
  payload: any;
}

interface Summary {
  total_traces: number;
  coverage_ratio: number;
}

interface AttributionData {
  summary: Summary;
  traces: Trace[];
}

export default function Attribution() {
  const [data, setData] = useState<AttributionData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/decision/attribution-lineage?limit=50`)
      .then(res => res.json())
      .then(data => setData(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <GitBranch size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        ATTRIBUTION_LINEAGE
      </h2>

      <div className="grid grid-cols-2">
        <div className="stat-card">
          <div className="stat-label">TOTAL_TRACE_EVENTS</div>
          <div className="stat-value">{data?.summary.total_traces || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">LINEAGE_COVERAGE</div>
          <div className="stat-value text-info">{((data?.summary.coverage_ratio || 0) * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="border-box" style={{ marginTop: '2rem' }}>
        <h3 className="text-secondary" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Layers size={18} /> EVENT_LOG
        </h3>
        
        <table className="terminal-table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>STAGE</th>
              <th>STRATEGY</th>
              <th>PAYLOAD</th>
            </tr>
          </thead>
          <tbody>
            {data?.traces.map((trace, idx) => (
              <tr key={idx}>
                <td className="text-muted" style={{ whiteSpace: 'nowrap' }}>
                  {new Date(trace.time).toLocaleTimeString()}
                </td>
                <td>
                  <span style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.4rem',
                    color: trace.action.includes('error') ? 'var(--accent-alert)' : 'var(--text-primary)'
                  }}>
                    {trace.action.includes('execution') ? <Zap size={12}/> : <Target size={12}/>}
                    {trace.action.toUpperCase()}
                  </span>
                </td>
                <td className="text-info">{trace.strategy_id}</td>
                <td>
                  <div style={{ 
                    fontSize: '0.75rem', 
                    maxWidth: '400px', 
                    overflow: 'hidden', 
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {JSON.stringify(trace.payload)}
                  </div>
                </td>
              </tr>
            ))}
            {(!data || data.traces.length === 0) && !loading && (
              <tr><td colSpan={4} className="text-muted">_NO_ATTRIBUTION_COVERAGE_FOUND</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {loading && <div className="blink">_SYNCHRONIZING_TRACE_DATABASE...</div>}
    </div>
  );
}
