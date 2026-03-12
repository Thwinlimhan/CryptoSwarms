import { MessageSquare, CheckCircle, XCircle, Info } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface Vote {
  solver_id: string;
  stance: string;
  confidence: number;
  rationale: string;
}

interface Round {
  round: number;
  dissent_solver_ids: string[];
  votes: Vote[];
}

interface CouncilData {
  decision: string;
  confidence: number;
  dissent_ratio: number;
  reason: string;
  rounds: Round[];
}

export default function Council() {
  const [data, setData] = useState<CouncilData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDebate = () => {
    setLoading(true);
    fetch(`${API_URL}/api/decision/debate-preview`)
      .then(res => res.json())
      .then(data => setData(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDebate();
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <MessageSquare size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        DECISION_COUNCIL_DEBATE
      </h2>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <button onClick={fetchDebate} disabled={loading}>
          {loading ? "[SYNCHRONIZING...]" : "TRIGGER_NEW_DEBATE_SIM"}
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-1">
          <div className="border-box" style={{ borderColor: data.decision === 'go' ? 'var(--text-primary)' : 'var(--accent-alert)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              RESULT: {data.decision.toUpperCase()} 
              {data.decision === 'go' ? <CheckCircle className="text-primary"/> : <XCircle className="text-danger"/>}
            </h3>
            <div className="text-muted" style={{ marginTop: '0.5rem' }}>
              AGREEMENT_CONFIDENCE: {(data.confidence * 100).toFixed(1)}% | DISSENT: {(data.dissent_ratio * 100).toFixed(1)}%
            </div>
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--bg-panel-border)' }}>
              {data.reason}
            </div>
          </div>

          {data.rounds.map((round, rIdx) => (
            <div key={rIdx} className="border-box" style={{ marginTop: '1.5rem' }}>
              <h4 className="text-secondary" style={{ marginBottom: '1rem' }}>ROUND_{round.round + 1} // AGENT_VOTES</h4>
              <div className="grid grid-cols-2">
                {round.votes.map((vote, vIdx) => (
                  <div key={vIdx} style={{ padding: '1rem', border: '1px solid var(--bg-panel-border)', backgroundColor: 'var(--bg-panel)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span className="text-info">{vote.solver_id.toUpperCase()}</span>
                      <span className={vote.stance === 'go' ? 'text-primary' : 'text-danger'}>
                        {vote.stance.toUpperCase()} ({(vote.confidence * 100).toFixed(0)}%)
                      </span>
                    </div>
                    <div className="text-muted" style={{ fontSize: '0.85rem', fontStyle: 'italic' }}>
                      "{vote.rationale}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!data && !loading && (
        <div className="text-warn">
          <Info size={16} /> NO_DEBATE_DATA_AVAILABLE
        </div>
      )}
    </div>
  );
}
