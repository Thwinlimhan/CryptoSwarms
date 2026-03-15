import { useState } from 'react';
import { 
  RefreshCw, 
  Trash2, 
  Wallet, 
  Activity, 
  Repeat,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
  ShieldAlert
} from 'lucide-react';
import { apiRequest } from '../api';
import { useApi } from '../hooks/useApi';
import { 
  StatCard, 
  DataTable, 
  StatusBadge, 
  PageHeader 
} from '../components/ui';

interface PaperStatus {
  status: string;
  wallet: string;
  mode: string;
  account_value: string;
  positions: any[];
  recent_fills: any[];
  message?: string;
}

export default function PaperTrading() {
  const { data: status, loading, refresh } = useApi<PaperStatus>('/api/paper/status', 5000);
  const [resetting, setResetting] = useState(false);

  const resetAccount = async () => {
    if (!window.confirm("Are you sure you want to reset the paper trading account? This will wipe all orders, positions, and balances.")) return;
    
    setResetting(true);
    try {
      const data = await apiRequest<{ status?: string }>('/api/paper/reset', { method: 'POST' });
      console.log("Reset result:", data);
      setTimeout(refresh, 1000);
    } catch (e) {
      console.error("Reset failed:", e);
    } finally {
      setResetting(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin mb-4" />
        <p className="text-slate-400 font-mono animate-pulse">_TUNING_TO_HYPERLIQUID_FEED...</p>
      </div>
    );
  }

  if (status?.status === 'offline') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 text-center max-w-md mx-auto">
        <div className="p-4 rounded-full bg-red-500/10 border border-red-500/20">
          <ShieldAlert size={48} className="text-red-500" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">HYPAPER_OFFLINE</h2>
          <p className="text-slate-400 font-mono text-sm uppercase tracking-tighter">
            The paper trading backend (HyPaper) is unreachable. 
            Ensure the <code className="bg-slate-800 px-1 rounded text-cyan-400">hypaper</code> service is running in Docker.
          </p>
        </div>
        <button 
          onClick={() => refresh()}
          className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg border border-slate-700 transition-all font-mono text-xs"
        >
          RETRY_CONNECTION
        </button>
      </div>
    );
  }

  const positionColumns = [
    { header: 'Coin', key: 'coin', render: (s: any) => <span className="font-bold text-white">{s.position.coin}</span> },
    { header: 'Size', key: 'sgl', render: (s: any) => {
        const sz = parseFloat(s.position.sgl);
        return <div className="flex items-center gap-2">
          {sz >= 0 ? <TrendingUp size={14} className="text-green-400" /> : <TrendingDown size={14} className="text-red-400" />}
          <span className={sz >= 0 ? "text-green-400" : "text-red-400"}>{sz}</span>
        </div>
      }
    },
    { header: 'Entry', key: 'entryPx', render: (s: any) => `$${parseFloat(s.position.entryPx).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})}` },
    { header: 'Unrealized PnL', key: 'unrealizedPnl', render: (s: any) => {
        const pnl = parseFloat(s.position.unrealizedPnl);
        return <span className={pnl >= 0 ? "text-green-400 font-mono" : "text-red-400 font-mono"}>
          {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
        </span>
      }
    },
    { header: 'Leverage', key: 'leverage', render: (s: any) => <span className="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">{s.position.leverage.value}x {s.position.leverage.type}</span> },
  ];

  const fillColumns = [
    { header: 'Time', key: 'time', render: (s: any) => <span className="text-slate-500 font-mono text-[10px]">{new Date(s.time).toLocaleTimeString()}</span> },
    { header: 'Coin', key: 'coin', render: (s: any) => <span className="font-bold">{s.coin}</span> },
    { header: 'Side', key: 'side', render: (s: any) => <StatusBadge status={s.side === 'B' ? 'BUY' : 'SELL'} variant={s.side === 'B' ? 'success' : 'error'} /> },
    { header: 'Price', key: 'px', render: (s: any) => <span className="font-mono text-cyan-400">${parseFloat(s.px).toFixed(s.px < 1 ? 4 : 2)}</span> },
    { header: 'Size', key: 'sz', render: (s: any) => <span className="font-mono">{s.sz}</span> },
    { header: 'PnL', key: 'closedPnl', render: (s: any) => {
        const pnl = parseFloat(s.closedPnl);
        if (pnl === 0) return <span className="text-slate-600">-</span>;
        return <span className={pnl >= 0 ? "text-green-400" : "text-red-400"}>
          {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
        </span>
      }
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader 
        title="HYPERLIQUID_COMMAND" 
        description="Paper trading interface powered by HyPaper. 1:1 API compatibility for testing swarm strategies."
        actions={
          <button 
            onClick={resetAccount}
            disabled={resetting}
            className="flex items-center gap-2 px-6 py-2 border border-red-500 bg-red-500/10 hover:bg-red-500 hover:text-black font-bold text-[10px] tracking-widest transition-all"
          >
            {resetting ? <RefreshCw size={12} className="animate-spin" /> : <Trash2 size={12} />}
            [RESET_PAPER_ACCOUNT]
          </button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          title="Account Value" 
          value={`$${parseFloat(status?.account_value || "0").toLocaleString(undefined, {minimumFractionDigits: 2})}`} 
        />
        <StatCard 
          title="Active Positions" 
          value={status?.positions.length || 0} 
        />
        <StatCard 
          title="Execution Mode" 
          value={status?.mode.toUpperCase() || "PAPER"} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h3 className="text-[10px] font-bold text-white mb-4 flex items-center gap-2 font-mono tracking-widest uppercase">
              <ShoppingBag size={14} className="text-cyan-400" /> [OPEN_POSITIONS]
            </h3>
            <DataTable 
              data={status?.positions || []} 
              columns={positionColumns} 
              emptyMessage="No active positions on Hyperliquid."
            />
          </section>

          <section>
            <h3 className="text-[10px] font-bold text-white mb-4 flex items-center gap-2 font-mono tracking-widest uppercase">
              <Repeat size={14} className="text-purple-400" /> [RECENT_FILLS]
            </h3>
            <DataTable 
              data={status?.recent_fills || []} 
              columns={fillColumns} 
              emptyMessage="No recent fills recorded."
            />
          </section>
        </div>

        <div className="space-y-6">
          <div className="p-6 border border-slate-800 bg-black">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <ShieldAlert size={14} /> [ADAPTER_LOGS]
            </h3>
            <div className="space-y-4 font-mono text-[9px]">
              <div className="p-2 bg-black/40 rounded border border-slate-800 text-green-500">
                [SYS] HYPERLIQUID_ADAPTER: INITIALIZED
              </div>
              <div className="p-2 bg-black/40 rounded border border-slate-800 text-cyan-500">
                [SYS] ENDPOINT: HYPERLIQUID_ACTIVE
              </div>
              <div className="p-2 bg-black/40 rounded border border-slate-800 text-slate-500">
                [SYS] POLLING_INTERVAL: 5000ms
              </div>
              <div className="p-2 bg-black/40 rounded border border-slate-800 text-yellow-500/80">
                [SYS] WARNING: RUNNING IN PAPER MODE. REAL MONEY NOT AT RISK.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
