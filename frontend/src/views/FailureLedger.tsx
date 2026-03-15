import { 
  Target, TrendingUp, TrendingDown, 
  HelpCircle, AlertCircle, BarChart3, 
  Layers, Filter
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { 
  StatCard, DataTable, StatusBadge, 
  PageHeader 
} from '../components/ui';

interface Decision {
  id: string;
  time: string;
  label: string;
  symbol: string;
  ev_estimate: number;
  win_probability: number;
  position_size_usd: number;
  status: 'pending' | 'won' | 'lost' | 'cancelled';
  pnl_usd: number | null;
  bias_flags: string[];
  notes: string | null;
  resolved_at: string | null;
}

interface LedgerStats {
  count: number;
  net_luck: number;
  calibration_error: number;
  actual_win_rate: number;
  expected_win_rate: number;
}

export default function FailureLedger() {
  const { data: decisions } = useApi<Decision[]>('/api/failure-ledger/decisions', 10000);
  const { data: stats } = useApi<LedgerStats>('/api/failure-ledger/stats', 30000);

  const columns = [
    { 
      header: 'Decision', 
      key: 'label', 
      render: (d: Decision) => (
        <div className="flex flex-col">
          <span className="font-bold text-white">{d.label}</span>
          <span className="text-[10px] text-slate-500 font-mono tracking-tighter">{d.id.slice(0, 8)}</span>
        </div>
      ) 
    },
    { header: 'Symbol', key: 'symbol', render: (d: Decision) => <span className="text-cyan-400 font-mono">{d.symbol}</span> },
    { 
      header: 'Calibration', 
      key: 'calibration', 
      render: (d: Decision) => (
        <div className="flex flex-col">
          <span className="text-xs text-slate-300">P(Win): {(d.win_probability * 100).toFixed(0)}%</span>
          <span className="text-xs text-slate-500">EV: ${d.ev_estimate.toFixed(2)}</span>
        </div>
      )
    },
    { 
      header: 'Status', 
      key: 'status', 
      render: (d: Decision) => <StatusBadge status={d.status} variant={d.status === 'won' ? 'success' : d.status === 'lost' ? 'error' : 'info'} /> 
    },
    { 
      header: 'Result', 
      key: 'pnl_usd', 
      render: (d: Decision) => (
        <div className={`font-mono font-bold ${d.pnl_usd && d.pnl_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {d.pnl_usd ? `${d.pnl_usd >= 0 ? '+' : ''}$${d.pnl_usd.toFixed(2)}` : '--'}
        </div>
      )
    },
    {
      header: 'Quality',
      key: 'bias',
      render: (d: Decision) => (
        <div className="flex gap-1">
          {Array.isArray(d.bias_flags) && d.bias_flags.map(bias => (
            <span key={bias} className="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
              {bias}
            </span>
          ))}
          {(!d.bias_flags || d.bias_flags.length === 0) && <span className="text-[9px] text-slate-600 italic">None</span>}
        </div>
      )
    }
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader 
        title="FAILURE_LEDGER" 
        description="Audit decision quality vs market outcomes. Identify cognitive biases and performance luck."
        actions={
          <button className="flex items-center gap-2 px-6 py-2 border border-slate-900 bg-slate-950/20 hover:bg-[#ff9d00] hover:text-black font-bold text-[10px] tracking-widest transition-all">
            <Filter size={12} /> [FILTER_BY_STRATEGY]
          </button>
        }
      />

      {/* Calibration Review */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Net Luck" 
          value={stats?.net_luck !== undefined ? `${stats.net_luck >= 0 ? '+' : ''}$${stats.net_luck.toFixed(2)}` : '--'} 
          icon={stats?.net_luck && stats.net_luck >= 0 ? <TrendingUp size={20} className="text-green-400" /> : <TrendingDown size={20} className="text-red-400" />}
          variant={stats?.net_luck && stats.net_luck >= 0 ? "success" : "danger"}
          subValue="Actual PnL - Expected PnL"
        />
        <StatCard 
          title="Calibration Error" 
          value={stats?.calibration_error !== undefined ? `${(stats.calibration_error * 100).toFixed(1)}%` : '--'} 
          icon={<Target size={20} className="text-cyan-400" />}
          variant="primary"
          subValue="Predicted vs Actual Win Rate"
        />
        <StatCard 
          title="Actual Win Rate" 
          value={stats?.actual_win_rate !== undefined ? `${(stats.actual_win_rate * 100).toFixed(1)}%` : '--'} 
          icon={<BarChart3 size={20} className="text-yellow-400" />}
          variant="warning"
        />
        <StatCard 
          title="Avg Bias Density" 
          value="1.2" 
          icon={<Layers size={20} className="text-purple-400" />}
          variant="primary"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Ledger Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-[10px] font-bold text-white flex items-center gap-2 font-mono tracking-widest uppercase">
              <AlertCircle size={14} className="text-cyan-400" /> [DECISION_LOG]
            </h3>
          </div>
          <DataTable 
            data={decisions || []} 
            columns={columns} 
            emptyMessage="No decisions recorded in ledger."
          />
        </div>

        {/* Cognitive Biases */}
        <div className="space-y-6">
          <div className="p-6 border border-slate-800 bg-black">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <HelpCircle size={14} /> [BIAS_DISTRIBUTION]
            </h3>
            <div className="space-y-4">
              {[
                { label: 'Recency Bias', count: 12, color: 'bg-red-900' },
                { label: 'FOMO', count: 8, color: 'bg-orange-500' },
                { label: 'Confirmation Bias', count: 5, color: 'bg-yellow-500' },
                { label: 'Sunk Cost Fallacy', count: 3, color: 'bg-blue-500' },
              ].map((bias) => (
                <div key={bias.label} className="space-y-2">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">{bias.label}</span>
                    <span className="text-white">{bias.count} signals</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-900 overflow-hidden border border-slate-800">
                    <div className={`h-full ${bias.color}`} style={{ width: `${(bias.count / 15) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
