import React, { useState } from 'react';
import { Clock } from 'lucide-react';

export const FundingAnalyzer: React.FC = () => {
    const [rate, setRate] = useState(0.0001); // 0.01% per 8h
    const [positionSize, setPositionSize] = useState(50000); // $50k position
    const [days, setDays] = useState(7);
    const [side, setSide] = useState<'long' | 'short'>('long');

    const intervalRate = rate;
    const dailyRate = intervalRate * 3; // Assuming 8h intervals
    const totalRate = dailyRate * days;
    const costUsd = positionSize * totalRate;
    const apr = dailyRate * 365 * 100;

    return (
        <div className="card" style={{ marginBottom: '2rem' }}>
            <div className="card-header">
                <h2>Funding EV Analyzer</h2>
                <span className="badge badge-primary">Module C2</span>
            </div>
            <div className="card-body">
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
                    <div className="flex-column-gap-1">
                        <div>
                            <label>8h Funding Rate (%)</label>
                            <input type="number" step="0.0001" value={rate * 100} onChange={e => setRate((parseFloat(e.target.value) || 0) / 100)} />
                        </div>
                        <div>
                            <label>Position Size (USD)</label>
                            <input type="number" value={positionSize} onChange={e => setPositionSize(parseFloat(e.target.value) || 0)} />
                        </div>
                        <div>
                            <label>Estimated Duration (Days)</label>
                            <input type="number" value={days} onChange={e => setDays(parseFloat(e.target.value) || 0)} />
                        </div>
                    </div>
                    <div className="flex-column-gap-1">
                        <label>Side Selection</label>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button 
                                onClick={() => setSide('long')}
                                style={{ flex: 1, background: side === 'long' ? 'rgba(0,255,65,0.1)' : 'transparent', borderColor: side === 'long' ? 'var(--text-primary)' : 'var(--bg-panel-border)' }}
                            >
                                LONG
                            </button>
                            <button 
                                onClick={() => setSide('short')}
                                style={{ flex: 1, background: side === 'short' ? 'rgba(255,0,60,0.1)' : 'transparent', borderColor: side === 'short' ? 'var(--accent-alert)' : 'var(--bg-panel-border)' }}
                            >
                                SHORT
                            </button>
                        </div>
                        <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-panel)', borderRadius: '8px' }}>
                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>ANNUALIZED_YIELD_APR</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: rate > 0 ? (side === 'long' ? 'var(--accent-alert)' : 'var(--text-primary)') : 'var(--text-muted)' }}>
                                {rate > 0 ? (side === 'long' ? '-' : '+') : ''}{Math.abs(apr).toFixed(2)}%
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2" style={{ gap: '1rem' }}>
                    <div className="stat-card" style={{ padding: '1.5rem', borderColor: side === 'long' ? 'var(--accent-alert)' : 'var(--text-primary)' }}>
                        <div className="stat-label">CARRY_COST_USD</div>
                        <div className="stat-value" style={{ color: side === 'long' ? '#ef4444' : '#10b981' }}>
                            {side === 'long' ? '-' : '+'}${Math.abs(costUsd).toFixed(2)}
                        </div>
                    </div>
                    <div className="stat-card" style={{ padding: '1.5rem' }}>
                        <div className="stat-label">DAILY_EQUIVALENT</div>
                        <div className="stat-value" style={{ fontSize: '1.2rem' }}>
                            ${(Math.abs(costUsd) / days).toFixed(2)} / day
                        </div>
                    </div>
                </div>

                <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(0,186,255,0.05)', border: '1px solid var(--accent-info)', borderRadius: '8px', fontSize: '0.85rem' }}>
                    <div className="flex-center-gap-05" style={{ color: 'var(--accent-info)', marginBottom: '0.5rem' }}>
                        <Clock size={16} /> HOLDING_IMPACT_VERDICT
                    </div>
                    {side === 'long' && rate > 0.0003 ? 
                        "CAUTION: High positive funding. Your strategy must overcome -0.1%+ daily theta decay." : 
                        "NOMINAL: Carry costs are within threshold. Focus on price delta."}
                </div>

            </div>
        </div>
    );
};
