import { Database, Network } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface ReadinessCheck {
  redis: boolean;
  timescaledb: boolean;
  neo4j: boolean;
  qdrant: boolean;
  sglang: boolean;
}

export default function DataSources() {
  const [readiness, setReadiness] = useState<ReadinessCheck | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health/ready`)
      .then(res => res.json())
      .then(data => setReadiness(data.checks))
      .catch(console.error);
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <Database size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        DATA_NODES
      </h2>

      <div className="grid grid-cols-2">
        <div className="border-box">
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--text-secondary)', paddingBottom: '0.5rem' }}>
            <Network size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/>
            DATABASE_TOPOLOGY
          </h3>
          <table className="terminal-table" style={{ width: '100%', tableLayout: 'fixed' }}>
             <thead><tr><th>NODE</th><th>TYPE</th><th>STATUS</th></tr></thead>
             <tbody>
                <tr>
                   <td>TSDB_CORE</td><td className="text-secondary">Timescale</td>
                   <td className={readiness?.timescaledb ? 'text-primary' : 'text-danger'}>
                      {readiness ? (readiness.timescaledb ? 'ONLINE' : 'OFFLINE') : 'WAIT...'}
                   </td>
                </tr>
                <tr>
                   <td>REDIS_MQ</td><td className="text-secondary">Stream</td>
                   <td className={readiness?.redis ? 'text-primary' : 'text-danger'}>
                      {readiness ? (readiness.redis ? 'ONLINE' : 'OFFLINE') : 'WAIT...'}
                   </td>
                </tr>
                <tr>
                   <td>QDRANT_M0</td><td className="text-secondary">Vector</td>
                   <td className={readiness?.qdrant ? 'text-primary' : 'text-danger'}>
                      {readiness ? (readiness.qdrant ? 'ONLINE' : 'OFFLINE') : 'WAIT...'}
                   </td>
                </tr>
                <tr>
                   <td>NEO4J_GD</td><td className="text-secondary">Graph</td>
                   <td className={readiness?.neo4j ? 'text-primary' : 'text-danger'}>
                      {readiness ? (readiness.neo4j ? 'ONLINE' : 'OFFLINE') : 'WAIT...'}
                   </td>
                </tr>
             </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
