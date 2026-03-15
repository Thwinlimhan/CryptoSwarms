import { Search, Shield, Activity, Zap, TrendingUp } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { StatCard, PageHeader, DataTable } from '../components/ui';

interface ResearchData {
  regime: string;
  detected_patterns: string[];
  whale_trades: { type: string, size: string, value: string, time: string }[];
  funding_rates: { symbol: string, rate: string, opportunity: string }[];
  guardian_status: { system: string, warnings: number, leaks: number, last_scan: string, scan_count?: number };
  hot_assets: { symbol: string, price: string, change: string, volume_24h?: number }[];
}

export default function ResearchHub() {
  const { data, loading, error } = useApi<ResearchData>('/api/research/latest', 5000);

  if (loading || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Activity className="w-8 h-8 text-[#ff9d00] animate-spin mb-4" />
        <p className="text-[#ff9d00] font-mono animate-pulse">_INITIALIZING_SEARCH_SWARM...</p>
      </div>
    );
  }

  const fundingColumns = [
    { header: 'SYMBOL', key: 'symbol' },
    { header: 'RATE', key: 'rate', render: (f: any) => <span className="text-red-500">{f.rate}</span> },
    { header: 'OPPORTUNITY', key: 'opportunity', render: (f: any) => <span className={f.opportunity === 'HIGH' ? 'text-white' : 'text-amber-500'}>{f.opportunity}</span> },
  ];

  return (
    <div className="animate-in fade-in duration-500 space-y-8">
      <PageHeader 
        title="RESEARCH_HUB" 
        description="SWARM INTELLIGENCE // REAL-TIME DISCOVERY"
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard title="MARKET_REGIME" value={data.regime} variant="primary" />
        <StatCard title="WHALE_VOLUME_24H" value="$1.48B" variant="primary" />
        <StatCard title="SIGNALS_GEN" value="42" variant="primary" />
        <StatCard title="RISK_LEVEL" value="MEDIUM" variant="danger" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column */}
        <div className="space-y-6">
          <div className="p-6 border border-[#ff9d00]/30 bg-black min-h-[200px]">
            <h3 className="text-[#00ff41] text-[10px] font-black uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <Zap size={14} /> AGENT_DISCOVERIES
            </h3>
            <div className="flex flex-wrap gap-2">
              {Array.isArray(data.detected_patterns) && data.detected_patterns.length > 0 ? (
                data.detected_patterns.map((p, i) => (
                  <span key={i} className="px-2 py-1 border border-[#00ff41]/40 text-[#00ff41] text-[10px] font-mono">
                    {p}
                  </span>
                ))
              ) : (
                <div className="text-[#00ff41] font-mono text-[9px] border border-[#00ff41]/20 p-2 animate-pulse w-full">
                  Waiting for first scan cycle...
                </div>
              )}
            </div>
          </div>

          <div className="p-6 border border-[#ff9d00]/30 bg-black">
            <h3 className="text-slate-600 text-[10px] font-black uppercase tracking-[0.2em] mb-6">WHALE_TRADE_TRACES</h3>
            <div className="space-y-4">
              {Array.isArray(data.whale_trades) && data.whale_trades.map((w, i) => (
                <div key={i} className="flex justify-between items-center text-[10px] font-mono border-b border-white/5 pb-2">
                  <span className={w.type === 'BUY' ? 'text-white' : 'text-red-500'}>{w.type} {w.size}</span>
                  <span className="text-slate-400">{w.value}</span>
                  <span className="text-slate-600">{w.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column */}
        <div className="p-6 border border-[#ff9d00]/30 bg-black">
          <h3 className="text-[#00ff41] text-[10px] font-black uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
             <Activity size={14} /> FUNDING_INEFFICIENCIES
          </h3>
          <DataTable 
            data={data.funding_rates || []} 
            columns={fundingColumns} 
            emptyMessage="No inefficiencies detected"
          />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <div className="p-6 border border-red-500/30 bg-black" style={{ borderLeft: '4px solid #ff3b3b' }}>
            <h3 className="text-red-500 text-[10px] font-black uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <Shield size={14} /> GUARDIAN_OVERWATCH
            </h3>
            <div className="space-y-6">
               <div className="flex items-center gap-3">
                 <div className="w-2 h-2 rounded-full bg-[#ff9d00] animate-pulse"></div>
                 <span className="text-xs font-mono text-white">SYSTEM_INTEGRITY: {data.guardian_status.system.toUpperCase()}</span>
               </div>
               <div className="pl-5 border-l border-slate-900 space-y-2">
                 <div className="text-slate-500 text-[10px] uppercase font-mono tracking-widest">• {data.guardian_status.warnings} ACTIVE_WARNINGS</div>
                 <div className="text-red-500 text-[10px] uppercase font-mono tracking-widest">• {data.guardian_status.leaks} MEMORY_FRAGMENTATION</div>
                 <div className="text-slate-600 font-mono text-[8px] mt-4">LAST_SCAN: {data.guardian_status.scan_count || 75} cycles completed</div>
               </div>
            </div>
          </div>

          <div className="p-6 border border-[#ff9d00]/30 bg-black">
             <h3 className="text-slate-600 text-[10px] font-black uppercase tracking-[0.2em] mb-6">HOT_FLOWS</h3>
             <div className="space-y-3">
               {Array.isArray(data.hot_assets) && data.hot_assets.map((a, i) => (
                 <div key={i} className="flex justify-between items-center bg-white/2 p-2 border border-white/5">
                    <div className="flex flex-col">
                      <span className="text-amber-500 font-bold text-[10px]">{a.symbol}</span>
                      <span className="text-slate-600 text-[8px] font-mono">{a.price}</span>
                    </div>
                    <span className={`text-[10px] font-mono ${a.change?.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>
                      {a.change}
                    </span>
                 </div>
               ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
