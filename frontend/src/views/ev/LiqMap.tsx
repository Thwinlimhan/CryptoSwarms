import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Flame } from 'lucide-react';

const MOCK_LIQ_DATA = [
    { price: 62000, value: 15.4 },
    { price: 62500, value: 42.1 },
    { price: 63000, value: 12.0 },
    { price: 63500, value: 85.3 }, // Cluster
    { price: 64000, value: 200.5 }, // Massive Cluster
    { price: 64500, value: 50.2 },
    { price: 65000, value: 12.1 },
    { price: 65500, value: 8.5 },
    { price: 66000, value: 145.2 }, // High Lev Shorts
    { price: 66500, value: 18.2 },
];

export const LiqMap: React.FC = () => {
    return (
        <div className="card" style={{ marginBottom: '2rem' }}>
            <div className="card-header">
                <h2>Liquidation Map & Cascade</h2>
                <span className="badge badge-primary">Module C3</span>
            </div>
            <div className="card-body">
                
                <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Flame className="text-danger" size={20} />
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>MAGNET_ZONE_DETECTION (v6_LOCAL)</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: 'rgba(255,0,0,0.1)', border: '1px solid #ef4444', color: '#ef4444' }}>
                        HIGH_VOLATILITY_PROBABILITY
                    </div>
                </div>

                <div style={{ height: '300px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={MOCK_LIQ_DATA} layout="vertical">
                            <XAxis type="number" hide />
                            <YAxis dataKey="price" type="category" stroke="var(--text-muted)" fontSize={10} width={50} />
                            <Tooltip 
                                cursor={{ fill: 'transparent' }}
                                contentStyle={{ backgroundColor: 'var(--surface-color)', borderColor: 'var(--border-color)' }}
                                formatter={(val: any) => [`$${val}M`, 'Liquidation Liquidity']}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                {MOCK_LIQ_DATA.map((entry, index) => (
                                    <Cell 
                                        key={`cell-${index}`} 
                                        fill={entry.value > 100 ? 'rgba(239, 68, 68, 0.8)' : 'rgba(255, 176, 0, 0.4)'} 
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div style={{ marginTop: '1.5rem', border: '1px solid var(--bg-panel-border)', padding: '1rem', borderRadius: '8px', background: 'var(--bg-panel)' }}>
                    <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>CASCADE_PROXIMITY</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--accent-alert)' }}>92.4%</span>
                    </div>
                    <div style={{ width: '100%', height: '4px', background: 'var(--bg-color)', borderRadius: '2px' }}>
                        <div style={{ width: '92.4%', height: '100%', background: 'linear-gradient(to right, #fbbf24, #ef4444)', borderRadius: '2px' }}></div>
                    </div>
                    <p style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                         $64,000 contains a major liquidation cluster (&gt;200M). A sweep of this level is highly likely to trigger a chain reaction to $63,500.
                    </p>
                </div>

            </div>
        </div>
    );
};
