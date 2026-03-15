import React, { useState } from 'react';
import type { EvScenario } from '../../utils/probability';
import { calculateEV, validateProbabilities } from '../../utils/probability';
import { PlusCircle, Trash2, ArrowRight } from 'lucide-react';

export const EvCalculator: React.FC = () => {
  const [scenarios, setScenarios] = useState<EvScenario[]>([
    { id: '1', description: 'Bull Flag Breakout Hits Target 1', probability: 0.3, payoff: 1500 },
    { id: '2', description: 'Consolidates (Scratch Trade)', probability: 0.4, payoff: -50 },
    { id: '3', description: 'Stops Out at Invalidation', probability: 0.3, payoff: -600 },
  ]);

  const isValid = validateProbabilities(scenarios);
  const totalEV = calculateEV(scenarios);
  
  const currentSum = scenarios.reduce((acc: number, s: EvScenario) => acc + s.probability, 0);

  const handleUpdate = (id: string, field: keyof EvScenario, value: string | number) => {
    setScenarios(scenarios.map((s: EvScenario) => {
      if (s.id !== id) return s;
      
      let parsedValue = typeof value === 'string' ? parseFloat(value) : value;
      if (isNaN(parsedValue as number)) parsedValue = 0;

      return { ...s, [field]: field === 'description' ? value : parsedValue };
    }));
  };

  const addScenario = () => {
    setScenarios([...scenarios, { id: Math.random().toString(), description: 'New Scenario', probability: 0, payoff: 0 }]);
  };

  const removeScenario = (id: string) => {
    setScenarios(scenarios.filter((s: EvScenario) => s.id !== id));
  };

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <div className="card-header">
        <h2>Core EV Calculator</h2>
        <span className="badge badge-primary">Module 01</span>
      </div>
      <div className="card-body">
        
        {!isValid && (
          <div className="status-banner status-fail" style={{ marginBottom: '1rem' }}>
            <strong>Validation Error:</strong> Probabilities must sum exactly to 1.0 (Currently: {currentSum.toFixed(3)})
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
          {scenarios.map((s: EvScenario, idx: number) => (
            <div key={s.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) 1fr 1fr auto', gap: '1rem', alignItems: 'center', background: 'var(--surface-color)', padding: '0.75rem', borderRadius: '8px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Scenario {idx + 1}</label>
                <input 
                  type="text" 
                  value={s.description} 
                  onChange={(e) => handleUpdate(s.id, 'description', e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Probability (0-1)</label>
                <input 
                  type="number" 
                  step="0.05"
                  value={s.probability} 
                  onChange={(e) => handleUpdate(s.id, 'probability', e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Payoff ($)</label>
                <input 
                  type="number"
                  value={s.payoff} 
                  onChange={(e) => handleUpdate(s.id, 'payoff', e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }}
                />
              </div>
              <button 
                onClick={() => removeScenario(s.id)}
                className="action-btn"
                style={{ marginTop: '1.2rem', padding: '0.5rem' }}
                title="Remove"
              >
                <Trash2 size={18} color="var(--danger-color)" />
              </button>
            </div>
          ))}
        </div>

        <button onClick={addScenario} className="action-btn" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
          <PlusCircle size={16} /> Add Scenario
        </button>

        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>
            System Expected Value (EV)
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 'bold', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '1rem',
            color: /*totalEV > 0 ? 'var(--success-color)' :*/ (totalEV === 0 ? 'var(--text-muted)' : (totalEV > 0 ? '#10b981' : '#ef4444'))
          }}>
            <ArrowRight size={24} />
            ${totalEV.toFixed(2)}
          </div>
        </div>

      </div>
    </div>
  );
};
