import React from 'react';
import { PieChart as PieIcon } from 'lucide-react';

export const OnChainSignals: React.FC = () => {
    const signals = [
        { label: 'Cumulative Volume Delta (CVD)', status: 'Bullish', score: 82, source: 'Binance Perps' },
        { label: 'Exchange Netflow (In/Out)', status: 'Neutral', score: 50, source: 'CryptoQuant' },
        { label: 'Open Interest Delta', status: 'Aggressive Long', score: 91, source: 'CoinGlass' },
        { label: 'Whale Tx Count (>1M)', status: 'Increasing', score: 68, source: 'WhaleAlert' },
    ];

    const avgConviction = signals.reduce((acc, s) => acc + s.score, 0) / signals.length;

    return (
        <div className="card" style={{ marginBottom: '2rem' }}>
            <div className="card-header">
                <h2>On-Chain Signal Aggregator</h2>
                <span className="badge badge-primary">Module C4</span>
            </div>
            <div className="card-body">
                
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '2rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {signals.map((s, idx) => (
                            <div key={idx} style={{ padding: '0.75rem', background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                                <div className="flex-between" style={{ marginBottom: '0.4rem' }}>
                                    <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{s.label}</span>
                                    <span style={{ fontSize: '0.75rem', color: s.score > 70 ? 'var(--text-primary)' : (s.score < 40 ? 'var(--accent-alert)' : 'var(--text-muted)') }}>
                                        {s.status.toUpperCase()}
                                    </span>
                                </div>
                                <div style={{ width: '100%', height: '4px', background: 'var(--bg-color)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ width: `${s.score}%`, height: '100%', background: s.score > 70 ? 'var(--text-primary)' : (s.score < 40 ? 'var(--accent-alert)' : 'var(--accent-info)') }}></div>
                                </div>
                                <div style={{ marginTop: '0.3rem', fontSize: '0.65rem', color: 'var(--text-muted)' }}>SOURCE: {s.source}</div>
                            </div>
                        ))}
                    </div>

                    <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', background: 'rgba(0,0,0,0.1)', borderRadius: '12px', border: '1px solid var(--bg-panel-border)' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>AGGREGATED_CONVICTION</div>
                        <div style={{ 
                            fontSize: '3rem', 
                            fontWeight: 'bold', 
                            color: avgConviction > 70 ? 'var(--text-primary)' : 'white',
                            textShadow: avgConviction > 70 ? '0 0 15px rgba(0,255,65,0.3)' : 'none'
                        }}>
                            {avgConviction.toFixed(0)}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>BULLISH_SKEW</div>
                        
                        <div style={{ marginTop: '1.5rem', opacity: 0.5 }}>
                            <PieIcon size={48} />
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};
