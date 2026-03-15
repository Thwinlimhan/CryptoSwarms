import { TerminalSquare, ChevronRight, TrendingUp, Activity } from 'lucide-react';
import { useState } from 'react';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

import { useApi } from '../hooks/useApi';
import { apiRequest } from '../api';
interface Strategy {
  id: string;
  name: string;
  group: string;
  last_run: string;
}

interface BacktestResult {
  _synthetic?: boolean;
  _warning?: string;
  strategy_id: string;
  total_pnl?: number | null;
  sharpe?: number | null;
  win_rate?: number | null;
  trades?: number | null;
  max_drawdown?: number | null;
  equity_curve?: { date: string; pnl: number; drawdown: number }[];
}

export default function Backtest() {
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  const { data: fetchStrategies } = useApi<Strategy[]>('/api/backtest/strategies', 0);
  const strategies = fetchStrategies || [];

  const handleSelect = (strat: Strategy) => {
    setSelectedStrategy(strat);
    setLoading(true);
    apiRequest<BacktestResult>(`/api/backtest/results/${strat.id}`)
      .then(data => setResults(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const runLiveBacktest = async () => {
    if (!selectedStrategy) return;
    setRunning(true);
    setResults(null);
    try {
      const data = await apiRequest<BacktestResult>(`/api/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_id: selectedStrategy.id,
          days: 14,
        }),
      });
      setResults(data);
    } catch (e) {
      console.error('Backtest run failed:', e);
      setResults({
        _synthetic: true,
        _warning: e instanceof Error ? e.message : 'Backtest failed. Check API and strategy id.',
        strategy_id: selectedStrategy.id,
        total_pnl: 0,
        sharpe: 0,
        win_rate: 0,
        trades: 0,
        max_drawdown: 0,
        equity_curve: [],
      });
    } finally {
      setRunning(false);
    }
  };

  // Group strategies by group
  const grouped = Array.isArray(strategies) ? strategies.reduce((acc, obj) => {
    const key = obj.group;
    if (!acc[key]) acc[key] = [];
    acc[key].push(obj);
    return acc;
  }, {} as Record<string, Strategy[]>) : {};

  return (
    <div className="flex-column-gap-2">
      <header>
        <h2 className="flex-center-gap-05">
          <TerminalSquare size={24} /> 
          STRATEGY_QUANTS_CONSOLE
        </h2>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '2rem', alignItems: 'start' }}>
        {/* Strategy List Sidebar */}
        <div className="border-box p-0">
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--bg-panel-border)', background: 'var(--bg-panel)' }}>
            <h4 style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>STRATEGY_GROUPS</h4>
          </div>
          <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
            {Object.keys(grouped).length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', fontSize: '0.8rem', opacity: 0.5 }}>
                NO_STRATEGIES_LOADED
              </div>
            ) : Object.entries(grouped).map(([group, list]) => (
              <div key={group}>
                <div style={{ 
                  padding: '0.5rem 1rem', 
                  fontSize: '0.7rem', 
                  background: 'rgba(255,255,255,0.03)', 
                  color: 'var(--accent-info)',
                  borderBottom: '1px solid var(--bg-panel-border)'
                }}>
                  {group.toUpperCase()}
                </div>
                {list.map(strat => (
                  <div 
                    key={strat.id}
                    onClick={() => handleSelect(strat)}
                    style={{ 
                      padding: '1rem', 
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--bg-panel-border)',
                      background: selectedStrategy?.id === strat.id ? 'var(--bg-highlight)' : 'transparent',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div style={{ fontSize: '0.85rem' }}>{strat.name}</div>
                    <ChevronRight size={14} className="text-muted" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Results Pane */}
        <div className="main-results">
          {!selectedStrategy && (
            <div className="border-box" style={{ textAlign: 'center', padding: '4rem', opacity: 0.5 }}>
              <Activity size={48} style={{ margin: '0 auto 1rem', display: 'block' }}/>
              _SELECT_STRATEGY_TO_INITIALIZE_QUANT_ENGINE
            </div>
          )}

          {selectedStrategy && (
            <div className="flex-column-gap-15">
              <div className="border-box flex-between">
                <div>
                  <h3 className="m-0">{selectedStrategy.name}</h3>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>ID: {selectedStrategy.id} // GROUP: {selectedStrategy.group}</div>
                </div>
                <button 
                  onClick={runLiveBacktest} 
                  disabled={running}
                  style={{ background: 'var(--text-primary)', color: 'black', border: 'none' }}
                >
                  {running ? "RE-SIMULATING..." : "RUN_BACKTEST"}
                </button>
              </div>

              {results?._synthetic && (
                <div style={{ 
                  background: 'rgba(255,165,0,0.1)', 
                  border: '1px solid rgba(255,165,0,0.5)', 
                  color: 'orange', 
                  padding: '1rem', 
                  fontSize: '0.85rem' 
                }}>
                  <strong>SYNTHETIC DATA: </strong> 
                  {results._warning || "This data is generated for demo purposes. Not based on real backtests."}
                </div>
              )}

              {loading && <div className="blink">_FETCHING_STATISTICAL_MODELS...</div>}

              {results && !loading && (
                <>
                  <div className="grid grid-cols-4">
                    <div className="stat-card">
                      <div className="stat-label">TOTAL_PNL</div>
                      <div className="stat-value text-primary">${typeof results.total_pnl === 'number' ? results.total_pnl.toFixed(2) : "0.00"}</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-label">SHARPE_RATIO</div>
                      <div className="stat-value">{typeof results.sharpe === 'number' ? results.sharpe.toFixed(2) : "0.00"}</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-label">WIN_RATE</div>
                      <div className="stat-value text-info">{(typeof results.win_rate === 'number' ? results.win_rate * 100 : 0).toFixed(1)}%</div>
                    </div>
                    <div className="stat-card" style={{ borderColor: 'var(--accent-alert)' }}>
                      <div className="stat-label">MAX_DRAWDOWN</div>
                      <div className="stat-value text-danger">{typeof results.max_drawdown === 'number' ? results.max_drawdown.toFixed(2) : "0.00"}</div>
                    </div>
                  </div>

                  {/* Unified Intelligence Hub */}
                  <div className="border-box" style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)' }}>
                    <header style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--bg-panel-border)', paddingBottom: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Activity className="text-primary" size={20} />
                        <h3 style={{ margin: 0, letterSpacing: '0.1em' }}>STRATEGY_INTELLIGENCE_REPORT</h3>
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--accent-info)', background: 'rgba(0,255,65,0.05)', padding: '0.2rem 0.6rem', border: '1px solid var(--accent-info)' }}>
                        LIVE_MARKET_BACKSET_V6
                      </div>
                    </header>

                    <div className="flex-column-gap-2">
                      {/* Section 1: Visual Performance */}
                      <div style={{ height: '450px' }}>
                        <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          <TrendingUp size={16} /> EQUITY_GROWTH_MODEL
                        </h4>
                        <ResponsiveContainer width="100%" height="90%">
                          <AreaChart data={results.equity_curve || []}>
                            <defs>
                              <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#00ff41" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#00ff41" stopOpacity={0}/>
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                            <XAxis dataKey="date" stroke="#444" fontSize={10} axisLine={false} tickLine={false} />
                            <YAxis stroke="#444" fontSize={10} axisLine={false} tickLine={false} />
                            <Tooltip 
                              contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #333' }}
                              itemStyle={{ color: '#00ff41' }}
                            />
                            <Area type="monotone" dataKey="pnl" stroke="#00ff41" strokeWidth={2} fillOpacity={1} fill="url(#colorPnl)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
