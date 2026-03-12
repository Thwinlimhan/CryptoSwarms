import { DollarSign, Flame } from 'lucide-react';
import { useState, useEffect } from 'react';

const API_URL = "http://127.0.0.1:8000";

interface BudgetData {
  spent_usd: number;
  daily_budget_usd: number;
  alert_threshold_usd: number;
  alert: boolean;
  blocked: boolean;
}

interface CostEvent {
  agent: string;
  model: string;
  total_usd: number;
}

export default function Costs() {
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [dailyCosts, setDailyCosts] = useState<CostEvent[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/costs/budget?spent_usd=0.09`)
      .then(res => res.json())
      .then(data => setBudget(data))
      .catch(console.error);

    fetch(`${API_URL}/api/costs/daily`)
      .then(res => res.json())
      .then(data => setDailyCosts(data))
      .catch(console.error);
  }, []);

  return (
    <div>
      <h2 style={{ marginBottom: "2rem" }}>
        <DollarSign size={24} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> 
        LLM_BURN_RATES
      </h2>

      <div className="grid grid-cols-2">
        <div className="border-box">
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--text-secondary)', paddingBottom: '0.5rem' }}>
            <Flame size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/>
            BUDGET_GUARD
          </h3>
          {budget ? (
            <div style={{ fontSize: '1.2rem', lineHeight: '2' }}>
              <div>SPENT: <span className={budget.alert ? "text-warn" : "text-primary"}>${budget.spent_usd.toFixed(4)}</span></div>
              <div>DAILY_ALLOTMENT: <span className="text-muted">${budget.daily_budget_usd.toFixed(2)}</span></div>
              <div>ALERT_THRESHOLD: <span className="text-muted">${budget.alert_threshold_usd.toFixed(2)}</span></div>
              <div>CIRCUIT_BREAKER_TRIPPED: <span className={budget.blocked ? "text-danger" : "text-primary"}>{budget.blocked ? "YES" : "NO"}</span></div>
            </div>
          ) : (
            <div className="blink">_LOADING BUDGET...</div>
          )}
        </div>

        <div className="border-box">
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--text-secondary)', paddingBottom: '0.5rem' }}>
             AGENT_COST_BREAKDOWN
          </h3>
          <table className="terminal-table" style={{ width: '100%' }}>
             <thead><tr><th>AGENT</th><th>INFERENCE_NODE</th><th>USD ($)</th></tr></thead>
             <tbody>
                {dailyCosts.map((c, i) => (
                  <tr key={i}>
                    <td className="text-secondary">{c.agent.toUpperCase()}</td>
                    <td>{c.model}</td>
                    <td className="text-primary">${c.total_usd.toFixed(4)}</td>
                  </tr>
                ))}
                {dailyCosts.length === 0 && (
                  <tr><td colSpan={3} className="text-muted">No cost data reported.</td></tr>
                )}
             </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
