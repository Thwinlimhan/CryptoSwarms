import React, { useState, useMemo } from 'react';

// Bayes' Theorem: P(A|B) = [P(B|A) * P(A)] / P(B)
// P(A) = prior probability
// P(B|A) = likelihood of evidence given hypothesis
// P(B|not A) = likelihood of evidence given null hypothesis
// Posterior = (Likelihood * Prior) / ((Likelihood * Prior) + (P(B|not A) * (1 - Prior)))

export const BayesianUpdater: React.FC = () => {
  const [prior, setPrior] = useState<number>(0.3); // Base rate (e.g., breakout success rate)
  
  const [evidenceBlocks, setEvidenceBlocks] = useState([
    { id: '1', name: 'High Volume Node Cleared', likelihood: 0.8, falsePositiveRate: 0.2 },
    { id: '2', name: 'Funding Rate Inverted', likelihood: 0.6, falsePositiveRate: 0.4 },
  ]);

  const addEvidence = () => {
    setEvidenceBlocks([...evidenceBlocks, { id: Math.random().toString(), name: 'New Evidence', likelihood: 0.5, falsePositiveRate: 0.5 }]);
  };

  const updateEvidence = (id: string, field: string, value: string | number) => {
    setEvidenceBlocks(evidenceBlocks.map((e) => {
      if (e.id === id) {
        return { ...e, [field]: value };
      }
      return e;
    }));
  };

  const removeEvidence = (id: string) => {
    setEvidenceBlocks(evidenceBlocks.filter(e => e.id !== id));
  };


  const { posteriors, finalPosterior } = useMemo(() => {
    const p = [];
    let currentPrior = prior;
    
    for (const ev of evidenceBlocks) {
      // Bayesian update step
      const pEvidenceGivenH = ev.likelihood;
      const pEvidenceGivenNotH = ev.falsePositiveRate;
      
      const numerator = pEvidenceGivenH * currentPrior;
      const denominator = numerator + (pEvidenceGivenNotH * (1 - currentPrior));
      
      let newPosterior = numerator / denominator;
      if (isNaN(newPosterior)) newPosterior = currentPrior;
      
      p.push(newPosterior);
      currentPrior = newPosterior;
    }
    
    return { posteriors: p, finalPosterior: currentPrior };
  }, [prior, evidenceBlocks]);


  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <div className="card-header">
        <h2>Bayesian Belief Updater</h2>
        <span className="badge badge-error">Module 03</span>
      </div>
      <div className="card-body">
        
        <div style={{ marginBottom: '1.5rem', padding: '1rem', background: 'var(--surface-color)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#8b5cf6', fontWeight: 'bold' }}>
              Base Rate / Prior Probability $\( P(H) \)$
            </label>
            <input 
              type="number" step="0.01" value={prior} onChange={e => setPrior(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }} 
            />
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              The unconditional probability of success before observing any unique indicators (e.g., 30% baseline win rate for breakouts).
            </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
          {evidenceBlocks.map((ev, idx) => (
            <div key={ev.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 100px auto', gap: '1rem', alignItems: 'center', background: 'var(--bg-color)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Evidence {idx + 1}</label>
                <input 
                  type="text" value={ev.name} onChange={e => updateEvidence(ev.id, 'name', e.target.value)}
                  style={{ width: '100%', padding: '0.4rem', background: 'var(--surface-color)', border: 'none', color: 'white' }} 
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }} title="P(E|H): Probability of seeing this IF the hypothesis is TRUE">Likelihood (True Pos %)</label>
                <input 
                  type="number" step="0.05" value={ev.likelihood} onChange={e => updateEvidence(ev.id, 'likelihood', parseFloat(e.target.value))}
                  style={{ width: '100%', padding: '0.4rem', background: 'var(--surface-color)', border: 'none', color: 'white' }} 
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }} title="P(E|~H): Probability of seeing this IF the hypothesis is FALSE">False Positive Rate</label>
                <input 
                  type="number" step="0.05" value={ev.falsePositiveRate} onChange={e => updateEvidence(ev.id, 'falsePositiveRate', parseFloat(e.target.value))}
                  style={{ width: '100%', padding: '0.4rem', background: 'var(--surface-color)', border: 'none', color: 'white' }} 
                />
              </div>
              
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Posterior</div>
                <div style={{ fontWeight: 'bold', color: '#8b5cf6' }}>{(posteriors[idx] * 100).toFixed(1)}%</div>
              </div>

              <button onClick={() => removeEvidence(ev.id)} className="action-btn" style={{ padding: '0.5rem' }}>&times;</button>
            </div>
          ))}
        </div>

        <button onClick={addEvidence} className="action-btn" style={{ marginBottom: '2rem' }}>+ Add Evidence Step</button>

        <div style={{ textAlign: 'center', padding: '1.5rem', background: 'rgba(139, 92, 246, 0.1)', border: '1px solid #8b5cf6', borderRadius: '8px' }}>
          <div style={{ fontSize: '1rem', color: '#8b5cf6', marginBottom: '0.5rem' }}>Final Calibrated Conviction</div>
          <div style={{ fontSize: '3rem', fontWeight: 'bold', textShadow: '0 0 10px rgba(139, 92, 246, 0.5)' }}>
            {(finalPosterior * 100).toFixed(2)}%
          </div>
        </div>

      </div>
    </div>
  );
};
