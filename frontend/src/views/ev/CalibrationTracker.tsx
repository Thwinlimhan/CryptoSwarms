import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const CALIBRATION_DATA = [
    { conviction: 0.1, actual: 0.08 },
    { conviction: 0.2, actual: 0.25 },
    { conviction: 0.3, actual: 0.28 },
    { conviction: 0.4, actual: 0.45 },
    { conviction: 0.5, actual: 0.52 },
    { conviction: 0.6, actual: 0.58 },
    { conviction: 0.7, actual: 0.65 },
    { conviction: 0.8, actual: 0.82 },
    { conviction: 0.9, actual: 0.88 },
];

export const CalibrationTracker: React.FC = () => {
    return (
        <div className="card" style={{ marginBottom: '2rem' }}>
            <div className="card-header">
                <h2>Calibration Tracker</h2>
                <span className="badge badge-warning">Module 08</span>
            </div>
            <div className="card-body">
                
                <div style={{ marginBottom: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    MEASURING_FORECAST_ACCURACY: Predicted Conviction vs. Realized Win Rate
                </div>

                <div style={{ height: '300px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                            <XAxis type="number" dataKey="conviction" name="Predicted" unit="%" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="var(--text-muted)" />
                            <YAxis type="number" dataKey="actual" name="Actual" unit="%" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="var(--text-muted)" />
                            <ZAxis range={[100, 100]} />
                            <Tooltip 
                                cursor={{ strokeDasharray: '3 3' }}
                                contentStyle={{ backgroundColor: 'var(--surface-color)', borderColor: 'var(--border-color)' }}
                            />
                            {/* Ideal Line 45 degree */}
                            <Scatter name="Calibration" data={CALIBRATION_DATA} fill="var(--text-primary)" />
                        </ScatterChart>
                    </ResponsiveContainer>
                </div>

                <div className="grid grid-cols-2" style={{ gap: '1rem', marginTop: '1rem' }}>
                    <div className="stat-card">
                        <div className="stat-label">BRIER_SCORE</div>
                        <div className="stat-value" style={{ fontSize: '1.2rem' }}>0.042</div>
                        <div style={{ fontSize: '0.65rem', color: '#10b981' }}>EXCELLENT (LOWER IS BETTER)</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">CALIBRATION_DRIFT</div>
                        <div className="stat-value" style={{ fontSize: '1.2rem', color: '#ef4444' }}>-3.2%</div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Slightly under-confident in bull regimes</div>
                    </div>
                </div>

                <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(251, 191, 36, 0.05)', border: '1px solid var(--accent-warning)', borderRadius: '8px', fontSize: '0.85rem' }}>
                    <div className="flex-center-gap-05" style={{ color: 'var(--accent-warning)', marginBottom: '0.5rem' }}>
                        <AlertTriangle size={16} /> CALIBRATION_ADVISORY
                    </div>
                    Systematic tendency to underestimate success in "Trending Up" regimes. Adjust Kelly sizing up by 5-10% to capture alpha.
                </div>

            </div>
        </div>
    );
};
