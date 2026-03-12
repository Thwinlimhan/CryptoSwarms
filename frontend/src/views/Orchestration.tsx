import { Cpu, Zap, Clock } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface SubagentResult {
  task_id: string;
  role: string;
  status: string;
  latency_ms: number;
}

interface PerformanceData {
  completed: number;
  failed: number;
  max_parallelism: number;
  total_latency_ms: number;
  saturation: number;
  queue_pressure_ratio: number;
  results: SubagentResult[];
}

export default function Orchestration() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);

  const runSim = (tasks = 6) => {
    setLoading(true);
    fetch(`${API_URL}/api/orchestration/subagents-preview?tasks=${tasks}`)
      .then(res => res.json())
      .then(data => setData(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    runSim(8);
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <Cpu size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        SWARM_ORCHESTRATION_PERF
      </h2>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <button onClick={() => runSim(4)} disabled={loading}>TRIGGER_LITE_SWARM (4)</button>
        <button onClick={() => runSim(12)} disabled={loading}>TRIGGER_HEAVY_SWARM (12)</button>
      </div>

      {data && (
        <div className="grid grid-cols-4">
          <div className="stat-card">
            <div className="stat-label">PARALLELISM</div>
            <div className="stat-value">{data.max_parallelism}x</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">QUEUE_SATURATION</div>
            <div className="stat-value text-info">{(data.saturation * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-card">
             <div className="stat-label">AVG_LATENCY</div>
             <div className="stat-value text-warn">
               {(data.total_latency_ms / (data.completed || 1)).toFixed(0)}ms
             </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">PRESSURE_RATIO</div>
            <div className="stat-value text-primary">{data.queue_pressure_ratio.toFixed(2)}</div>
          </div>
        </div>
      )}

      {data && (
        <div className="border-box" style={{ marginTop: '2rem' }}>
           <h3 className="text-secondary" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
             <Zap size={18} /> AGENT_WAVE_EXECUTION
           </h3>

           <div className="grid grid-cols-2" style={{ gap: '1rem' }}>
              {data.results.map((res, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '1rem', 
                  backgroundColor: 'var(--bg-panel)',
                  border: '1px solid var(--bg-panel-border)',
                  borderLeft: `4px solid ${res.status === 'completed' ? 'var(--text-primary)' : 'var(--accent-alert)'}`
                 }}>
                   <div>
                     <div className="text-info" style={{ fontSize: '0.75rem' }}>{res.task_id.toUpperCase()}</div>
                     <div style={{ fontWeight: 'bold' }}>{res.role.toUpperCase()}</div>
                   </div>
                   <div style={{ textAlign: 'right' }}>
                     <div className="text-primary" style={{ fontSize: '0.75rem' }}>
                       <Clock size={10} style={{ marginRight: '0.2rem' }}/> 
                       {res.latency_ms.toFixed(0)}ms
                     </div>
                     <div style={{ fontSize: '0.7rem' }}>{res.status.toUpperCase()}</div>
                   </div>
                </div>
              ))}
           </div>
        </div>
      )}

      {loading && <div className="blink">_ORCHESTRATING_SUBAGENT_WAVE...</div>}
    </div>
  );
}
