import { Share2, Box, Clock, Hash } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface DagNode {
  node_id: string;
  node_type: string;
  topic: string;
  content: string;
  created_at: string;
  metadata: any;
}

interface DagData {
  topic: string;
  node_count: number;
  nodes: DagNode[];
}

export default function MemoryDAG() {
  const [data, setData] = useState<DagData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDAG = () => {
    setLoading(true);
    fetch(`${API_URL}/api/decision/dag-preview?max_nodes=12`)
      .then(res => res.json())
      .then(data => setData(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDAG();
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <Share2 size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        MEMORY_DAG_EXPLORER
      </h2>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <button onClick={fetchDAG} disabled={loading}>
          {loading ? "[RECALLING_NODES...]" : "REFRESH_MEMORIES"}
        </button>
      </div>

      {data && (
        <div>
          <div className="grid grid-cols-1">
             <div className="border-box">
                <h3 className="text-secondary">SCOPE: {data.topic}</h3>
                <div className="text-muted">TOTAL_NODES_IN_GRAPH: {data.node_count}</div>
             </div>
          </div>

          <div className="grid grid-cols-1" style={{ marginTop: '1.5rem', gap: '1rem' }}>
            {data.nodes.map((node, idx) => (
              <div key={idx} className="border-box" style={{ padding: '1rem', position: 'relative' }}>
                <div style={{ position: 'absolute', top: '1rem', right: '1rem', opacity: 0.3 }}>
                  <Hash size={12} /> {node.node_id.split('-')[0]}
                </div>
                
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                   <span className="text-info" style={{ 
                     padding: '2px 8px', 
                     border: '1px solid var(--accent-info)', 
                     fontSize: '0.7rem' 
                   }}>
                     {node.node_type.toUpperCase()}
                   </span>
                   <span className="text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}>
                     <Clock size={12} /> {new Date(node.created_at).toLocaleTimeString()}
                   </span>
                </div>

                <div style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                  <Box size={14} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }}/>
                  {node.topic}
                </div>

                <div style={{ 
                  backgroundColor: 'rgba(0,0,0,0.3)', 
                  padding: '1rem', 
                  fontSize: '0.85rem', 
                  lineHeight: '1.4',
                  borderLeft: '2px solid var(--text-secondary)'
                }}>
                  {node.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && !data && <div className="blink">_PROBING_MEMORY_GRAPH...</div>}
    </div>
  );
}
