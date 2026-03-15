import { useState, useEffect } from 'react';
import { 
  ShieldAlert, Cpu, Play, Square, 
  RefreshCw, Zap, TrendingUp, Activity,
  Database, Brain
} from 'lucide-react';
import { apiRequest } from '../api';
import { useApi } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { 
  StatCard, DataTable, StatusBadge, 
  PageHeader 
} from '../components/ui';

interface AgentStatus {
  status: string;
  since: string | null;
  signals_today: number;
  last_heartbeat: string | null;
}

interface OverviewData {
  time: string;
  readiness: {
    ok: boolean;
    checks: Record<string, boolean>;
  };
  agent_status: Record<string, AgentStatus>;
  healthy_agent_count: number;
  total_agent_count: number;
  signals_today: number;
  dag_memory: {
    node_count: number;
    edge_count: number;
    recall_hit_rate: number;
  }
}

interface RunnerStatus {
  running: boolean;
  scan_count: number;
  last_regime: string;
  latest_signals: any[];
  hot_assets: any[];
}

export default function Dashboard() {
  const { data: overview, loading: loadingOverview } = useApi<OverviewData>('/api/dashboard/overview', 5000);
  const { data: runner } = useApi<RunnerStatus>('/api/agents/runner-status', 5000);
  
  // Real-time updates via WebSocket
  const { data: wsMessage } = useWebSocket<{ type: string; data?: unknown; hot_assets?: unknown }>('/ws/live');
  
  const [liveSignals, setLiveSignals] = useState<any[]>([]);
  const [strategicDecisions, setStrategicDecisions] = useState<any[]>([]);
  const [hotAssets, setHotAssets] = useState<any[]>([]);
  const [swarmStatus, setSwarmStatus] = useState<'idle' | 'starting' | 'running' | 'stopping'>('idle');

  useEffect(() => {
    if (wsMessage?.type === 'signals') {
      const list = Array.isArray(wsMessage.data) ? wsMessage.data : [];
      setLiveSignals(prev => [...list, ...prev].slice(0, 20));
      if (Array.isArray(wsMessage.hot_assets)) setHotAssets(wsMessage.hot_assets);
    }
    if (wsMessage?.type === 'strategic_decision' && wsMessage.data !== undefined) {
      setStrategicDecisions(prev => [wsMessage.data, ...prev].slice(0, 10));
    }
  }, [wsMessage]);

  useEffect(() => {
    if (runner?.running) setSwarmStatus('running');
    if (runner?.latest_signals && liveSignals.length === 0) setLiveSignals(runner.latest_signals);
    if (runner?.hot_assets) setHotAssets(runner.hot_assets);
  }, [runner]);

  const controlSwarm = async (action: 'start' | 'stop') => {
    setSwarmStatus(action === 'start' ? 'starting' : 'stopping');
    try {
      const result = await apiRequest<{ status: string }>(`/api/agents/control?action=${action}`, { method: 'POST' });
      if (result.status === 'SUCCESS') {
        setSwarmStatus(action === 'start' ? 'running' : 'idle');
      }
    } catch (e) {
      console.error("Swarm control failure:", e);
      setSwarmStatus('idle');
    }
  };

  if (loadingOverview || !overview) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin mb-4" />
        <p className="text-slate-400 font-mono animate-pulse">_CONNECTING TO SWARM...</p>
      </div>
    );
  }

  const signalColumns = [
    { header: 'Type', key: 'signal_type', render: (s: any) => <StatusBadge status={s.signal_type} variant={s.signal_type.includes('BUY') ? 'success' : 'info'} /> },
    { header: 'Symbol', key: 'symbol', render: (s: any) => <span className="font-bold text-white">{s.symbol}</span> },
    { header: 'Confidence', key: 'confidence', render: (s: any) => `${(s.confidence * 100).toFixed(1)}%` },
    { header: 'Priority', key: 'priority', render: (s: any) => <StatusBadge status={s.priority} variant={s.priority === 'HIGH' ? 'error' : 'warning'} /> },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader 
        title="SWARM_OVERVIEW" 
        description="Unified command center for real-time market scanning and risk management."
        actions={
          <div className="flex gap-2">
            {swarmStatus === 'running' ? (
              <button 
                onClick={() => controlSwarm('stop')}
                className="flex items-center gap-2 px-6 py-2 border border-red-500 bg-red-500/10 hover:bg-red-500 hover:text-black font-bold text-[10px] tracking-widest transition-all"
              >
                <Square size={12} fill="currentColor" /> [STOP_SWARM]
              </button>
            ) : (
              <button 
                onClick={() => controlSwarm('start')}
                disabled={swarmStatus === 'starting'}
                className="flex items-center gap-2 px-6 py-2 border border-[#ff9d00] bg-[#ff9d00]/10 hover:bg-[#ff9d00] hover:text-black font-bold text-[10px] tracking-widest transition-all"
              >
                {swarmStatus === 'starting' ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} fill="currentColor" />}
                [START_SWARM]
              </button>
            )}
          </div>
        }
      />

      {/* Primary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Active Agents" 
          value={`${overview.healthy_agent_count}/${overview.total_agent_count}`} 
        />
        <StatCard 
          title="Signals Today" 
          value={overview?.signals_today} 
        />
        <StatCard 
          title="Recall Rate" 
          value={overview?.dag_memory?.recall_hit_rate !== undefined ? `${(overview.dag_memory.recall_hit_rate * 100).toFixed(1)}%` : '--'} 
        />
        <StatCard 
          title="Market Regime" 
          value={runner?.last_regime || "UNKNOWN"} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Live Signals Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-[10px] font-black text-white flex items-center gap-2 tracking-[0.2em] font-mono">
              <TrendingUp size={14} className="text-[#ff9d00]" /> [LIVE_SIGNALS]
            </h3>
          </div>
          <DataTable 
            data={liveSignals} 
            columns={signalColumns} 
            emptyMessage="Waiting for market signals..."
          />

          <div className="pt-4">
            <h3 className="text-[10px] font-black text-white flex items-center gap-2 mb-4 tracking-[0.2em] font-mono">
              <Brain size={14} className="text-purple-400" /> [STRATEGIC_CONSOLE]
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {strategicDecisions.map((decision, idx) => (
                <div key={idx} className="p-4 border border-slate-900 bg-black hover:border-[#ff9d00]/40 transition-all group">
                  <div className="flex justify-between items-start mb-3 border-b border-slate-900 pb-2">
                    <div>
                      <div className="text-[8px] text-slate-600 font-mono tracking-tighter uppercase">{decision.strategy_id}</div>
                      <div className="text-md font-bold text-white font-mono">{decision.symbol}</div>
                    </div>
                    <StatusBadge status={decision.action} variant={decision.action === 'BUY' || decision.action === 'LONG' ? 'success' : 'error'} />
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="p-2 border border-slate-900 bg-slate-950/40">
                      <div className="text-[8px] text-slate-700 uppercase tracking-widest">Confidence</div>
                      <div className="text-md font-mono text-amber-500">{(decision.confidence * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-2 border border-slate-900 bg-slate-950/40">
                      <div className="text-[8px] text-slate-700 uppercase tracking-widest">Expected Value</div>
                      <div className="text-md font-mono text-green-500">${decision.expected_value.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              ))}
              {strategicDecisions.length === 0 && (
                <div className="col-span-2 py-12 text-center border border-dashed border-slate-900 bg-black/20">
                  <p className="text-slate-700 font-mono text-[9px] uppercase tracking-[0.3em] animate-pulse">_AWAITING_STRATEGIC_CONVICTION...</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status and Health */}
        <div className="space-y-6">
          <div className="p-6 border border-slate-900 bg-black">
            <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <ShieldAlert size={14} /> [SYSTEM_READINESS]
            </h3>
            <div className="space-y-3">
              {Object.entries(overview?.readiness?.checks || {}).map(([service, ok]) => (
                <div key={service} className="flex justify-between items-center bg-slate-950/30 p-2 border border-slate-900/50">
                  <span className="text-[9px] font-mono uppercase text-slate-500">{service}</span>
                  <StatusBadge status={ok ? "READY" : "OFFLINE"} variant={ok ? "success" : "error"} />
                </div>
              ))}
            </div>
          </div>

          <div className="p-6 border border-slate-900 bg-black">
            <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <Database size={14} /> [HOT_ASSETS]
            </h3>
            <div className="space-y-2">
              {hotAssets.map((asset, idx) => (
                <div key={idx} className="flex justify-between items-center p-2 hover:bg-slate-950/50 border border-transparent hover:border-slate-900 transition-colors">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-amber-500">{asset.symbol}</span>
                    <span className="text-[8px] text-slate-600 font-mono">LIVE_FEED</span>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-mono text-white">${parseFloat(asset.price).toLocaleString()}</div>
                    <div className={`text-[9px] font-mono ${parseFloat(asset.change) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {parseFloat(asset.change) >= 0 ? '+' : ''}{asset.change}%
                    </div>
                  </div>
                </div>
              ))}
              {hotAssets.length === 0 && (
                <div className="text-center py-4 text-[9px] text-slate-700 uppercase tracking-widest italic">_NO_PRICE_DATA_AVAILABLE_</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
