import { useState, useEffect, useMemo } from 'react';
import {
  Wallet, TrendingUp, TrendingDown, DollarSign,
  Shield, BarChart3, RefreshCw, ArrowUpRight,
  ArrowDownRight, Target, Clock, Zap
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  StatCard, DataTable, StatusBadge,
  PageHeader
} from '../components/ui';

interface Position {
  position_id: string;
  strategy_id: string;
  symbol: string;
  side: string;
  entry_price: number;
  size_usd: number;
  size_tokens: number;
  stop_loss: number;
  take_profit: number;
  unrealized_pnl: number;
  candles_held: number;
  entry_time: string;
}

interface Trade {
  trade_id: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  size_usd: number;
  pnl_usd: number;
  pnl_pct: number;
  exit_reason: string;
  exit_time: string;
  strategy_id: string;
}

interface RiskMetrics {
  total_exposure_usd: number;
  position_count: number;
  max_single_position_usd: number;
  concentration_risk: number;
  unrealized_pnl_usd: number;
  win_rate: number;
  profit_factor: number;
  total_closed_trades: number;
}

interface OrderData {
  client_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  price: number | null;
  status: string;
  strategy_id: string;
  created_at: string;
}

interface PortfolioData {
  timestamp: string;
  total_pnl_usd: number;
  open_positions: Position[];
  daily_pnl: any[];
  risk_metrics: RiskMetrics;
  trade_history: Trade[];
}

interface OrdersResponse {
  orders: OrderData[];
  stats: {
    total_orders: number;
    pending_count: number;
    filled_count: number;
    failed_count: number;
  };
}

interface WsPortfolioUpdate {
  type: string;
  data?: {
    total_pnl_usd: number;
    positions: Position[];
    risk_metrics: RiskMetrics;
  };
  event?: string;
}

export default function Portfolio() {
  const { data: portfolio, loading } = useApi<PortfolioData>('/api/portfolio/live', 5000);
  const { data: ordersData } = useApi<OrdersResponse>('/api/portfolio/orders', 10000);
  const { data: wsMessage } = useWebSocket<WsPortfolioUpdate>('/ws/live');

  // Real-time state from WebSocket
  const [livePnl, setLivePnl] = useState<number>(0);
  const [livePositions, setLivePositions] = useState<Position[]>([]);
  const [liveRisk, setLiveRisk] = useState<RiskMetrics | null>(null);
  const [orderEvents, setOrderEvents] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'positions' | 'trades' | 'orders'>('positions');

  // Process WebSocket messages
  useEffect(() => {
    if (!wsMessage) return;

    if (wsMessage.type === 'portfolio_update' && wsMessage.data) {
      setLivePnl(wsMessage.data.total_pnl_usd);
      setLivePositions(wsMessage.data.positions);
      setLiveRisk(wsMessage.data.risk_metrics);
    }

    if (wsMessage.type === 'order_event') {
      setOrderEvents(prev => [wsMessage, ...prev].slice(0, 30));
    }
  }, [wsMessage]);

  // Sync from REST on first load
  useEffect(() => {
    if (portfolio) {
      setLivePnl(portfolio.total_pnl_usd);
      setLivePositions(portfolio.open_positions);
      setLiveRisk(portfolio.risk_metrics);
    }
  }, [portfolio]);

  const risk = liveRisk || portfolio?.risk_metrics;
  const positions = livePositions.length > 0 ? livePositions : (portfolio?.open_positions || []);
  const trades = portfolio?.trade_history || [];
  const orders = ordersData?.orders || [];
  const orderStats = ordersData?.stats;

  // Derived stats
  const totalUnrealizedPnl = useMemo(() =>
    positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0),
    [positions]
  );

  if (loading || !portfolio) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin mb-4" />
        <p className="text-slate-400 font-mono animate-pulse text-[10px] tracking-[0.3em]">_LOADING_PORTFOLIO_DATA...</p>
      </div>
    );
  }

  const positionColumns = [
    {
      header: 'Symbol',
      key: 'symbol',
      render: (p: Position) => (
        <div className="flex flex-col">
          <span className="font-bold text-white text-[11px]">{p.symbol}</span>
          <span className="text-[8px] text-slate-600 font-mono">{p.strategy_id}</span>
        </div>
      )
    },
    {
      header: 'Side',
      key: 'side',
      render: (p: Position) => (
        <StatusBadge
          status={p.side}
          variant={p.side === 'LONG' || p.side === 'BUY' ? 'success' : 'error'}
        />
      )
    },
    {
      header: 'Entry',
      key: 'entry_price',
      render: (p: Position) => (
        <span className="font-mono text-white text-[10px]">${p.entry_price.toLocaleString()}</span>
      )
    },
    {
      header: 'Size',
      key: 'size_usd',
      render: (p: Position) => (
        <span className="font-mono text-slate-300 text-[10px]">${p.size_usd.toFixed(2)}</span>
      )
    },
    {
      header: 'Unrealized PnL',
      key: 'unrealized_pnl',
      render: (p: Position) => (
        <span className={`font-mono font-bold text-[10px] ${p.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
        </span>
      )
    },
    {
      header: 'SL / TP',
      key: 'stop_loss',
      render: (p: Position) => (
        <div className="flex flex-col text-[9px] font-mono">
          <span className="text-red-400">{p.stop_loss.toFixed(2)}</span>
          <span className="text-green-400">{p.take_profit.toFixed(2)}</span>
        </div>
      )
    },
    {
      header: 'Hold',
      key: 'candles_held',
      render: (p: Position) => (
        <span className="text-slate-500 font-mono text-[10px]">{p.candles_held}c</span>
      )
    },
  ];

  const tradeColumns = [
    {
      header: 'Symbol',
      key: 'symbol',
      render: (t: Trade) => <span className="font-bold text-white text-[10px]">{t.symbol}</span>
    },
    {
      header: 'Side',
      key: 'side',
      render: (t: Trade) => (
        <StatusBadge status={t.side} variant={t.side === 'LONG' ? 'success' : 'error'} />
      )
    },
    {
      header: 'Entry → Exit',
      key: 'entry_price',
      render: (t: Trade) => (
        <div className="font-mono text-[9px]">
          <span className="text-slate-400">${t.entry_price.toFixed(2)}</span>
          <span className="text-slate-600 mx-1">→</span>
          <span className="text-white">${t.exit_price.toFixed(2)}</span>
        </div>
      )
    },
    {
      header: 'PnL',
      key: 'pnl_usd',
      render: (t: Trade) => (
        <div className="flex flex-col">
          <span className={`font-mono font-bold text-[10px] ${t.pnl_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {t.pnl_usd >= 0 ? '+' : ''}${t.pnl_usd.toFixed(2)}
          </span>
          <span className={`font-mono text-[8px] ${t.pnl_pct >= 0 ? 'text-green-500/60' : 'text-red-500/60'}`}>
            {t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%
          </span>
        </div>
      )
    },
    {
      header: 'Reason',
      key: 'exit_reason',
      render: (t: Trade) => (
        <StatusBadge
          status={t.exit_reason.toUpperCase().replace('_', ' ')}
          variant={t.exit_reason === 'take_profit' ? 'success' : t.exit_reason === 'stop_loss' ? 'error' : 'warning'}
        />
      )
    },
  ];

  const orderColumns = [
    {
      header: 'Order ID',
      key: 'client_order_id',
      render: (o: OrderData) => (
        <span className="font-mono text-[9px] text-slate-400">{o.client_order_id.slice(-12)}</span>
      )
    },
    {
      header: 'Symbol',
      key: 'symbol',
      render: (o: OrderData) => <span className="font-bold text-white text-[10px]">{o.symbol}</span>
    },
    {
      header: 'Side',
      key: 'side',
      render: (o: OrderData) => (
        <StatusBadge status={o.side} variant={o.side === 'BUY' || o.side === 'LONG' ? 'success' : 'error'} />
      )
    },
    {
      header: 'Status',
      key: 'status',
      render: (o: OrderData) => {
        const variants: Record<string, 'success' | 'error' | 'warning' | 'info'> = {
          filled: 'success',
          failed: 'error',
          rejected: 'error',
          submitted: 'info',
          pending_submission: 'warning',
        };
        return <StatusBadge status={o.status.toUpperCase()} variant={variants[o.status] || 'info'} />;
      }
    },
    {
      header: 'Qty',
      key: 'quantity',
      render: (o: OrderData) => <span className="font-mono text-[10px] text-slate-300">{o.quantity.toFixed(6)}</span>
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title="PORTFOLIO_PNL"
        description="Real-time portfolio tracking, position management, and order lifecycle monitoring."
      />

      {/* Primary PnL Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total PnL"
          value={`${livePnl >= 0 ? '+' : ''}$${livePnl.toFixed(2)}`}
          variant={livePnl >= 0 ? 'success' : 'danger'}
          subValue="Realized PnL"
        />
        <StatCard
          title="Unrealized PnL"
          value={`${totalUnrealizedPnl >= 0 ? '+' : ''}$${totalUnrealizedPnl.toFixed(2)}`}
          variant={totalUnrealizedPnl >= 0 ? 'success' : 'danger'}
          subValue={`${positions.length} open positions`}
        />
        <StatCard
          title="Win Rate"
          value={risk ? `${risk.win_rate.toFixed(1)}%` : '--'}
          subValue={risk ? `${risk.total_closed_trades} trades` : ''}
        />
        <StatCard
          title="Exposure"
          value={risk ? `$${risk.total_exposure_usd.toFixed(0)}` : '--'}
          subValue={risk ? `PF: ${risk.profit_factor.toFixed(2)}` : ''}
        />
      </div>

      {/* Risk Meters */}
      {risk && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 border border-slate-900 bg-black">
            <div className="flex items-center gap-2 mb-2">
              <Shield size={12} className="text-amber-500" />
              <span className="text-[8px] text-slate-600 uppercase tracking-[0.2em] font-mono">CONCENTRATION</span>
            </div>
            <div className="flex items-end gap-2">
              <span className="text-lg font-black font-mono text-white">{risk.concentration_risk.toFixed(1)}%</span>
            </div>
            <div className="mt-2 h-1 bg-slate-900 overflow-hidden">
              <div
                className="h-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, risk.concentration_risk)}%`,
                  backgroundColor: risk.concentration_risk > 50 ? '#ef4444' : risk.concentration_risk > 30 ? '#f59e0b' : '#22c55e',
                }}
              />
            </div>
          </div>

          <div className="p-4 border border-slate-900 bg-black">
            <div className="flex items-center gap-2 mb-2">
              <Target size={12} className="text-cyan-500" />
              <span className="text-[8px] text-slate-600 uppercase tracking-[0.2em] font-mono">POSITIONS</span>
            </div>
            <span className="text-lg font-black font-mono text-white">{risk.position_count}</span>
          </div>

          <div className="p-4 border border-slate-900 bg-black">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={12} className="text-green-500" />
              <span className="text-[8px] text-slate-600 uppercase tracking-[0.2em] font-mono">MAX POSITION</span>
            </div>
            <span className="text-lg font-black font-mono text-white">${risk.max_single_position_usd.toFixed(0)}</span>
          </div>

          <div className="p-4 border border-slate-900 bg-black">
            <div className="flex items-center gap-2 mb-2">
              <Zap size={12} className="text-purple-500" />
              <span className="text-[8px] text-slate-600 uppercase tracking-[0.2em] font-mono">ORDERS</span>
            </div>
            <span className="text-lg font-black font-mono text-white">{orderStats?.total_orders || 0}</span>
            <div className="flex gap-2 mt-1 text-[8px] font-mono">
              <span className="text-green-500">{orderStats?.filled_count || 0} filled</span>
              <span className="text-red-400">{orderStats?.failed_count || 0} failed</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-slate-900 pb-0">
        {(['positions', 'trades', 'orders'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-2 text-[9px] font-black tracking-[0.2em] uppercase font-mono transition-all border-b-2 ${
              activeTab === tab
                ? 'text-[#ff9d00] border-[#ff9d00] bg-[#ff9d00]/5'
                : 'text-slate-600 border-transparent hover:text-slate-400 hover:border-slate-800'
            }`}
          >
            {tab === 'positions' && <Wallet size={10} className="inline mr-2" />}
            {tab === 'trades' && <BarChart3 size={10} className="inline mr-2" />}
            {tab === 'orders' && <Clock size={10} className="inline mr-2" />}
            {tab}
            {tab === 'positions' && positions.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 text-[8px] bg-[#ff9d00]/20 text-[#ff9d00]">{positions.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[300px]">
        {activeTab === 'positions' && (
          <DataTable
            data={positions}
            columns={positionColumns}
            emptyMessage="No open positions. The swarm is waiting for high-conviction signals..."
          />
        )}

        {activeTab === 'trades' && (
          <DataTable
            data={trades}
            columns={tradeColumns}
            emptyMessage="No closed trades yet. Positions will appear here after exits..."
          />
        )}

        {activeTab === 'orders' && (
          <DataTable
            data={orders}
            columns={orderColumns}
            emptyMessage="No orders recorded. Start the swarm to begin order tracking..."
          />
        )}
      </div>

      {/* Live Order Events Feed */}
      {orderEvents.length > 0 && (
        <div className="p-6 border border-slate-900 bg-black">
          <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
            <Zap size={14} className="text-amber-500" /> [LIVE_ORDER_FEED]
          </h3>
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {orderEvents.map((ev, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 border border-slate-900/50 bg-slate-950/30 hover:bg-slate-950/60 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {ev.event === 'filled' ? (
                    <ArrowUpRight size={12} className="text-green-500" />
                  ) : (
                    <ArrowDownRight size={12} className="text-red-500" />
                  )}
                  <span className="font-mono text-[9px] text-white">
                    {ev.data?.symbol || 'UNKNOWN'}
                  </span>
                  <StatusBadge
                    status={ev.event?.toUpperCase() || 'EVENT'}
                    variant={ev.event === 'filled' ? 'success' : 'error'}
                  />
                </div>
                <span className="text-[8px] text-slate-600 font-mono">
                  {ev.data?.client_order_id?.slice(-8) || ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
