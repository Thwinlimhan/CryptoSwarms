import { Code2, Settings } from 'lucide-react';
import { useState, useEffect } from 'react';

import { apiRequest } from '../api';

export default function CodeViewer() {
  const [config, setConfig] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    apiRequest<{ tasks?: unknown }>('/api/routing/policy')
      .then(data => {
        setConfig(JSON.stringify(data.tasks || data, null, 2));
      })
      .catch(err => {
        console.error(err);
        setConfig("// FAILED TO LOAD CONFIG FROM SERVER");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <Code2 size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        SYS_CONFIG
      </h2>

      <div className="grid grid-cols-1">
        <div className="border-box">
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--text-secondary)', paddingBottom: '0.5rem', display: 'flex', alignItems: 'center' }}>
            <Settings size={18} style={{ marginRight: '0.5rem' }}/> 
            SWARM_ROUTING_POLICY.JSON
          </h3>
          <pre style={{ 
            backgroundColor: 'var(--bg-primary)', 
            padding: '1rem', 
            border: '1px solid var(--text-muted)',
            overflowX: 'auto',
            minHeight: '200px'
          }}>
            <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
              {loading ? <span className="blink">_LOADING...</span> : config}
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
}
