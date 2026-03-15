import React, { useState } from 'react';
import { calculateKellyFraction } from '../../utils/probability';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export const KellySizer: React.FC = () => {
  const [winProb, setWinProb] = useState<number>(0.55);
  const [winReward, setWinReward] = useState<number>(200);
  const [lossPenalty, setLossPenalty] = useState<number>(100);

  const fullKelly = calculateKellyFraction(winProb, winReward, lossPenalty);
  const halfKelly = fullKelly / 2;
  const quarterKelly = fullKelly / 4;

  const data = React.useMemo(() => {
    let pts = [];
    
    // Simulating exponential growth trajectories for chart visualization
    let fCapital = 10000;
    let hCapital = 10000;
    let qCapital = 10000;
    
    // this is just an illustrative curve, not mathematically rigorous geometric growth given non-continuous compounding
    
    for(let i = 0; i <= 20; i++) {
        pts.push({
            trade: i,
            full: fCapital,
            half: hCapital,
            quarter: qCapital,
        });
        fCapital *= (1 + fullKelly * ((winProb * winReward) - ((1-winProb)*lossPenalty)) / 10000);
        hCapital *= (1 + halfKelly * ((winProb * winReward) - ((1-winProb)*lossPenalty)) / 10000);
        qCapital *= (1 + quarterKelly * ((winProb * winReward) - ((1-winProb)*lossPenalty)) / 10000);
    }
    return pts;
  }, [fullKelly, halfKelly, quarterKelly, winProb, winReward, lossPenalty]);

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <div className="card-header">
        <h2>Kelly Criterion Sizer</h2>
        <span className="badge badge-warning">Module 02</span>
      </div>
      <div className="card-body">
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
            <div>
              <label>Win Probability</label>
              <input 
                type="number" step="0.01" value={winProb} onChange={e => setWinProb(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))}
                style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }} 
              />
            </div>
            <div>
              <label>Avg Win Payoff ($)</label>
              <input 
                type="number" value={winReward} onChange={e => setWinReward(Math.max(1, parseFloat(e.target.value) || 0))} 
                style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }} 
              />
            </div>
            <div>
              <label>Avg Loss Penalty ($)</label>
              <input 
                type="number" value={lossPenalty} onChange={e => setLossPenalty(Math.max(1, parseFloat(e.target.value) || 0))} 
                style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: 'white' }} 
              />
            </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '2rem', textAlign: 'center' }}>
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.9rem', color: '#ef4444' }}>Full Kelly (Aggressive)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{(fullKelly * 100).toFixed(2)}%</div>
            </div>
            <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid #3b82f6', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.9rem', color: '#3b82f6' }}>Half Kelly (Balanced)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{(halfKelly * 100).toFixed(2)}%</div>
            </div>
            <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.9rem', color: '#10b981' }}>Quarter Kelly (Conservative)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{(quarterKelly * 100).toFixed(2)}%</div>
            </div>
        </div>

        <div style={{ height: 250 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="trade" stroke="var(--text-muted)" />
              <YAxis domain={['auto', 'auto']} stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--surface-color)', borderColor: 'var(--border-color)' }}
                itemStyle={{ color: 'var(--text-color)' }}
              />
              <Line type="monotone" dataKey="full" stroke="#ef4444" strokeWidth={2} dot={false} name="Full" />
              <Line type="monotone" dataKey="half" stroke="#3b82f6" strokeWidth={2} dot={false} name="Half" />
              <Line type="monotone" dataKey="quarter" stroke="#10b981" strokeWidth={2} dot={false} name="Quarter" />
            </LineChart>
          </ResponsiveContainer>
        </div>

      </div>
    </div>
  );
};
