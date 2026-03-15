import React, { useState } from 'react';
import { Target, ShieldAlert, TrendingUp } from 'lucide-react';

export const TradeSetup: React.FC = () => {
  const [entry, setEntry] = useState(65000);
  const [stop, setStop] = useState(63500);
  const [target, setTarget] = useState(70000);
  const [size, setSize] = useState(1.0); // units (e.g. 1 BTC)
  const [feeRate, setFeeRate] = useState(0.001); // 0.1%

  const riskPerUnit = Math.abs(entry - stop);
  const rewardPerUnit = Math.abs(target - entry);

  const totalRiskVal = riskPerUnit * size;
  const totalRewardVal = rewardPerUnit * size;
  
  const entryFee = entry * size * feeRate;
  const exitFee = target * size * feeRate;
  const stopFee = stop * size * feeRate;

  const netProfit = totalRewardVal - entryFee - exitFee;
  const netLoss = totalRiskVal + entryFee + stopFee;

  const feeAdjustedRR = netLoss > 0 ? (netProfit / netLoss) : 0;

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <div className="card-header">
        <h2>Asymmetric Trade Setup</h2>
        <span className="badge badge-primary">Module C1</span>
      </div>
      <div className="card-body">
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
            <div className="flex-column-gap-1">
                <div>
                   <label>Entry Price ($)</label>
                   <input type="number" value={entry} onChange={e => setEntry(parseFloat(e.target.value) || 0)} />
                </div>
                <div>
                   <label>Stop Loss ($)</label>
                   <input type="number" value={stop} onChange={e => setStop(parseFloat(e.target.value) || 0)} />
                </div>
                <div>
                   <label>Target Price ($)</label>
                   <input type="number" value={target} onChange={e => setTarget(parseFloat(e.target.value) || 0)} />
                </div>
            </div>
            <div className="flex-column-gap-1">
                <div>
                   <label>Position Size (Units)</label>
                   <input type="number" step="0.01" value={size} onChange={e => setSize(parseFloat(e.target.value) || 0)} />
                </div>
                <div>
                   <label>Taker/Maker Fee (%)</label>
                   <input type="number" step="0.001" value={feeRate * 100} onChange={e => setFeeRate((parseFloat(e.target.value) || 0) / 100)} />
                </div>
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>FEE_OVERHEAD_ESTIMATE</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-info)' }}>
                        ${(entryFee + exitFee).toFixed(2)}
                    </div>
                </div>
            </div>
        </div>

        <div className="grid grid-cols-3" style={{ gap: '1rem' }}>
            <div className="stat-card" style={{ padding: '1.5rem' }}>
                <div className="stat-label flex-center-gap-05"><ShieldAlert size={14} /> MAX_TOTAL_RISK</div>
                <div className="stat-value text-danger" style={{ fontSize: '1.5rem' }}>-${netLoss.toFixed(2)}</div>
            </div>
            <div className="stat-card" style={{ padding: '1.5rem' }}>
                <div className="stat-label flex-center-gap-05"><Target size={14} /> NET_TARGET_PROFIT</div>
                <div className="stat-value text-success" style={{ fontSize: '1.5rem' }}>+${netProfit.toFixed(2)}</div>
            </div>
            <div className="stat-card" style={{ padding: '1.5rem' }}>
                <div className="stat-label flex-center-gap-05"><TrendingUp size={14} /> SCORE_R:R</div>
                <div className="stat-value" style={{ fontSize: '1.5rem', color: feeAdjustedRR > 3 ? 'var(--text-primary)' : 'white' }}>
                    1 : {feeAdjustedRR.toFixed(2)}
                </div>
            </div>
        </div>

        <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(0,255,65,0.05)', border: '1px dashed var(--text-primary)', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-primary)', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>ASYMMETRIC_VERDICT</div>
            <div style={{ color: 'white', fontSize: '0.9rem' }}>
                {feeAdjustedRR >= 3 ? 
                    "STRONG_POS_SCORE: Trade maintains >3:1 ratio even after fees. Structurally sound." : 
                    "MARGINAL_SCORE: Asymmetry is weak. Consider adjusting entry or skipping."}
            </div>
        </div>

      </div>
    </div>
  );
};
