import { 
  Beaker, 
  ChevronRight, 
  CheckCircle2, 
  TrendingUp, 
  History,
  Brain,
  Zap,
  Shield,
  Clock
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { 
  StatCard, 
  StatusBadge, 
  PageHeader 
} from '../components/ui';
import { useState } from 'react';
import { apiRequest } from '../api';

interface Experiment {
  theme: string;
  variable: string;
  baseline_value: string;
  variant_value: string;
  score: number;
  delta_vs_baseline: number;
  metrics: any;
  status: string;
}

interface DagNode {
  node_id: string;
  node_type: string;
  topic: string;
  content: string;
  created_at: string;
  metadata: any;
}

interface ResearchReport {
  id: string;
  time: string;
  date: string;
  theme: string;
  data_source: string;
  summary: string;
  recommendation: string;
  regressions: string;
  safety_note: string;
  full_data: Experiment[];
  applied: boolean;
}

export default function ResearchLab() {
  const { data: reports, loading, refresh } = useApi<ResearchReport[]>('/api/research/reports', 5000);
  const { data: dag, refresh: refreshMemory } = useApi<{ nodes: DagNode[] }>('/api/research/memory', 10000);
  const [applying, setApplying] = useState<string | null>(null);

  const applyRefinement = async (nodeId: string) => {
    setApplying(nodeId);
    try {
      await apiRequest(`/api/research/refinements/${nodeId}/apply`, { method: 'POST' });
      alert("STRATEGY_UPDATED: Parameters written to source file.");
      refreshMemory();
    } catch (e) {
      console.error("Refinement apply failed:", e);
      alert("FAILED_TO_UPDATE_STRATEGY");
    } finally {
      setApplying(null);
    }
  };

  const applyRecommendation = async (id: string) => {
    setApplying(id);
    try {
      await apiRequest(`/api/research/reports/${id}/apply`, { method: 'POST' });
      setTimeout(refresh, 500);
    } catch (e) {
      console.error("Apply failed:", e);
    } finally {
      setApplying(null);
    }
  };

  if (loading && (!reports || reports.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Clock className="w-8 h-8 text-purple-500 animate-spin mb-4" />
        <p className="text-slate-400 font-mono animate-pulse uppercase tracking-widest text-xs">_RECALLING_NIGHTLY_EXPERIMENTS...</p>
      </div>
    );
  }

  const latestReport = reports?.[0];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader 
        title="RESEARCH_LAB" 
        description="Recursive improvement loop for decentralized agent configurations."
      />

      {/* Primary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard 
          title="Daily Experiments" 
          value={latestReport?.full_data?.length || 0} 
        />
        <StatCard 
          title="Improvement Delta" 
          value={latestReport?.full_data && Array.isArray(latestReport.full_data) && latestReport.full_data.length > 0
            ? `+${(Math.max(...latestReport.full_data.map(d => d.delta_vs_baseline || 0)) * 100).toFixed(1)}%` 
            : "0%"} 
        />
        <StatCard 
          title="Research Theme" 
          value={latestReport?.theme.split('_').join(' ').toUpperCase() || "IDLE"} 
        />
        <StatCard 
          title="Last Sync" 
          value={latestReport ? new Date(latestReport.time).toLocaleTimeString() : "NEVER"} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Latest Research Report */}
        <div className="lg:col-span-2 space-y-8">
          <section className="p-6 border border-slate-950 bg-black relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <Brain size={60} className="text-[#ff9d00]" />
            </div>
            
            <div className="flex justify-between items-start mb-6 border-b border-slate-900 pb-4">
              <div>
                <StatusBadge status="LATEST_PROPOSAL" variant="active" pulse />
                <h2 className="text-xl font-black text-white mt-2 font-mono tracking-widest uppercase">{latestReport?.theme.split('_').join(' ')}</h2>
                <p className="text-slate-600 font-mono text-[9px] uppercase tracking-widest mt-1">:: Agentic logic optimization proposal</p>
              </div>
              {latestReport && !latestReport.applied && (
                <button 
                  onClick={() => applyRecommendation(latestReport.id)}
                  disabled={!!applying}
                  className="px-6 py-2 border border-[#ff9d00] bg-[#ff9d00]/10 hover:bg-[#ff9d00] hover:text-black font-bold text-[10px] tracking-widest transition-all flex items-center gap-2"
                >
                  {applying === latestReport.id ? <Clock size={12} className="animate-spin" /> : <Zap size={12} />}
                  [APPROVE_&_DEPLOY]
                </button>
              )}
              {latestReport?.applied && (
                <div className="flex items-center gap-2 text-green-500 font-mono text-[10px] bg-green-500/5 px-4 py-2 border border-green-500/20 tracking-widest">
                  <CheckCircle2 size={12} /> [DEPLOYED_SUCCESSFULLY]
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 font-mono">
              <div className="space-y-2 border-l border-slate-900 pl-4">
                <h4 className="text-[9px] font-bold text-slate-700 uppercase tracking-widest">Finding Analysis</h4>
                <p className="text-slate-400 text-[11px] leading-relaxed">{latestReport?.summary}</p>
              </div>
              <div className="space-y-2 border-l border-[#ff9d00]/40 pl-4">
                <h4 className="text-[9px] font-bold text-[#ff9d00] uppercase tracking-widest">Optimization Strategy</h4>
                <p className="text-white text-[11px] font-medium bg-white/2 p-3 border border-white/5">{latestReport?.recommendation}</p>
              </div>
            </div>

            <div className="flex gap-4 font-mono">
              <div className="flex-1 p-3 bg-red-950/20 border border-red-900/40">
                <h4 className="text-[9px] font-bold text-red-500 uppercase tracking-widest mb-1">Regressions</h4>
                <p className="text-slate-600 text-[9px]">{latestReport?.regressions || "No regressions detected in sandbox."}</p>
              </div>
              <div className="flex-1 p-3 bg-amber-950/20 border border-amber-900/40">
                <h4 className="text-[9px] font-bold text-[#ff9d00] uppercase tracking-widest mb-1">Risk Assessment</h4>
                <p className="text-slate-600 text-[9px]">{latestReport?.safety_note}</p>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-[10px] font-bold text-white mb-4 flex items-center gap-2 font-mono tracking-[0.2em] uppercase">
              <ChevronRight size={14} className="text-[#ff9d00]" /> [ISOLATED_EXPERIMENTS]
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.isArray(latestReport?.full_data) && latestReport.full_data.map((exp, idx) => (
                <div key={idx} className="p-4 border border-slate-950 bg-black hover:border-slate-900 transition-all font-mono">
                  <div className="flex justify-between mb-3 border-b border-slate-950 pb-2">
                    <span className="text-[9px] font-bold text-slate-700 uppercase tracking-tighter">{exp.variable}</span>
                    <span className={`text-[9px] font-bold ${exp.delta_vs_baseline >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {exp.delta_vs_baseline >= 0 ? '+' : ''}{(exp.delta_vs_baseline * 100).toFixed(1)}% Δ
                    </span>
                  </div>
                  <div className="flex items-center gap-3 bg-slate-950/50 p-2 border border-slate-900">
                    <div className="flex-1 text-center">
                      <div className="text-[8px] text-slate-700 uppercase">Baseline</div>
                      <div className="text-[10px] text-slate-500 truncate">{exp.baseline_value}</div>
                    </div>
                    <ChevronRight size={10} className="text-slate-800" />
                    <div className="flex-1 text-center">
                      <div className="text-[8px] text-[#ff9d00] uppercase">Variant</div>
                      <div className="text-[10px] text-white truncate">{exp.variant_value}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* New: Strategy Refinements from DAG */}
          {dag && dag.nodes.some(n => n.node_type === 'strategy_refinement') && (
            <section className="space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Brain size={20} className="text-cyan-400" /> STRATEGY_REFINEMENTS
              </h3>
              <div className="space-y-4">
                {dag.nodes.filter(n => n.node_type === 'strategy_refinement').map((node, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-cyan-500/5 border border-cyan-500/10 hover:border-cyan-500/30 transition-all">
                    <div className="flex justify-between items-center mb-4">
                      <div className="flex items-center gap-3">
                        <StatusBadge status="PROPOSED_OPTIMIZATION" variant="active" />
                        <span className="text-white font-bold">{node.topic}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono italic">
                        via LLM Researcher
                      </span>
                    </div>

                    <p className="text-slate-300 text-sm mb-4 leading-relaxed">
                      {node.content}
                    </p>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-black/40 p-3 rounded-lg border border-white/5">
                        <div className="text-[8px] text-slate-500 uppercase tracking-widest mb-2">PROPOSED_PARAMETERS</div>
                        <pre className="text-[10px] text-cyan-300 font-mono overflow-x-auto">
                          {JSON.stringify(node.metadata.proposed_parameters, null, 2)}
                        </pre>
                      </div>
                      <div className="bg-black/40 p-3 rounded-lg border border-white/5">
                        <div className="text-[8px] text-slate-500 uppercase tracking-widest mb-2">RATIONALE_METRICS</div>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-[10px] text-slate-400">Confidence</span>
                            <span className="text-[10px] text-white font-bold">{(node.metadata.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-[10px] text-slate-400">Source</span>
                            <span className="text-[10px] text-slate-500 underline">{node.metadata.source_file}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <button 
                      onClick={() => applyRefinement(node.node_id)}
                      disabled={!!applying}
                      className="mt-4 w-full py-2 bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-400 border border-cyan-500/30 rounded-lg font-mono text-[10px] tracking-widest transition-all flex items-center justify-center gap-2"
                    >
                      {applying === node.node_id ? <Clock size={12} className="animate-spin" /> : <Zap size={12} />}
                      APPLY_OPTIMIZED_PARAMETERS
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Research History & Rules */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
              <History size={16} /> RESEARCH_HISTORY
            </h3>
            <div className="space-y-4">
              {reports?.slice(1, 5).map((r) => (
                <div key={r.id} className="flex items-center gap-4 p-3 rounded-xl hover:bg-slate-800/50 transition-all border border-transparent hover:border-slate-700">
                  <div className={`p-2 rounded-lg ${r.applied ? 'bg-green-500/10 text-green-500' : 'bg-slate-800 text-slate-500'}`}>
                    <CheckCircle2 size={16} />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">{r.theme.toUpperCase()}</div>
                    <div className="text-[10px] text-slate-500">{new Date(r.time).toLocaleDateString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-6 border border-slate-900 bg-black">
            <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <Shield size={14} className="text-[#ff9d00]" /> [RESEARCH_CONSTRAINTS]
            </h3>
            <ul className="space-y-3">
              {[
                "No auto-apply to production",
                "One variable at a time",
                "Never hide regressions",
                "Human approval mandatory",
                "Active hours off-limits"
              ].map((rule, i) => (
                <li key={i} className="flex items-center gap-3 text-[9px] text-slate-500 font-mono uppercase tracking-tight">
                  <div className="w-1 h-1 bg-amber-600" />
                  {rule}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
