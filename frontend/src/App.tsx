import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  Terminal,
  Activity,
  Database,
  Code2,
  Network,
  Users,
  Share2,
  GitBranch,
  Cpu,
  DollarSign,
  Search,
  Settings,
  Calculator,
  AlertTriangle,
  BarChart3,
  Beaker,
  Wallet
} from 'lucide-react';
import './App.css';

import { apiRequest } from './api';
import { ErrorBoundary } from './components/ErrorBoundary';

// Views
import Dashboard from './views/Dashboard';
import Backtest from './views/Backtest';
import DataSources from './views/DataSources';
import CodeViewer from './views/CodeViewer';
import Costs from './views/Costs';
import Council from './views/Council';
import MemoryDAG from './views/MemoryDAG';
import Attribution from './views/Attribution';
import Orchestration from './views/Orchestration';
import ResearchHub from './views/ResearchHub';
import SettingsView from './views/Settings';
import { MasterDashboard } from './views/ev/MasterDashboard';
import FailureLedger from './views/FailureLedger';
import PaperTrading from './views/PaperTrading';
import ResearchLab from './views/ResearchLab';
import Portfolio from './views/Portfolio';

function Sidebar() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0, color: '#ff9d00', fontWeight: '900', letterSpacing: '0.1em' }}>
          <Network size={20} />
          SWARM_OS
        </h2>
        <div className="text-slate-600 font-mono text-[8px] mt-2 uppercase tracking-widest">v6.0.0-rc1 // SECURE_SOCKET</div>
      </div>

      <nav className="sidebar-nav">
        <Link to="/" className={`nav-item ${path === '/' ? 'active' : ''}`}>
          <Terminal size={18} />
          <span>DASHBOARD</span>
        </Link>
        <Link to="/research" className={`nav-item ${path === '/research' ? 'active' : ''}`}>
          <Search size={18} />
          <span>AGENT_RESEARCH</span>
        </Link>
        <Link to="/backtest" className={`nav-item ${path === '/backtest' ? 'active' : ''}`}>
          <Activity size={18} />
          <span>BACKTEST</span>
        </Link>
        <Link to="/data" className={`nav-item ${path === '/data' ? 'active' : ''}`}>
          <Database size={18} />
          <span>DATA_NODES</span>
        </Link>
        <Link to="/code" className={`nav-item ${path === '/code' ? 'active' : ''}`}>
          <Code2 size={18} />
          <span>ROUTER_RULES</span>
        </Link>
        <Link to="/costs" className={`nav-item ${path === '/costs' ? 'active' : ''}`}>
          <DollarSign size={18} />
          <span>BURN_RATES</span>
        </Link>

        <div className="sidebar-divider">ANALYSIS_LAYERS</div>

        <Link to="/council" className={`nav-item ${path === '/council' ? 'active' : ''}`}>
          <Users size={18} />
          <span>DECISION_COUNCIL</span>
        </Link>
        <Link to="/ev" className={`nav-item ${path === '/ev' ? 'active' : ''}`}>
          <Calculator size={18} />
          <span>EV_MODEL</span>
        </Link>
        <Link to="/memory" className={`nav-item ${path === '/memory' ? 'active' : ''}`}>
          <Share2 size={18} />
          <span>MEMORY_DAG</span>
        </Link>
        <Link to="/attribution" className={`nav-item ${path === '/attribution' ? 'active' : ''}`}>
          <GitBranch size={18} />
          <span>ATTRIBUTION</span>
        </Link>
        <Link to="/orchestration" className={`nav-item ${path === '/orchestration' ? 'active' : ''}`}>
          <Cpu size={18} />
          <span>SWARM_ORCH</span>
        </Link>
        <Link to="/settings" className={`nav-item ${path === '/settings' ? 'active' : ''}`}>
          <Settings size={18} />
          <span>SETTINGS</span>
        </Link>
        <Link to="/failure-ledger" className={`nav-item ${path === '/failure-ledger' ? 'active' : ''}`}>
          <AlertTriangle size={18} />
          <span>FAILURE_LEDGER</span>
        </Link>
        <Link to="/research-lab" className={`nav-item ${path === '/research-lab' ? 'active' : ''}`}>
          <Beaker size={18} />
          <span>RESEARCH_LAB</span>
        </Link>
        <Link to="/paper" className={`nav-item ${path === '/paper' ? 'active' : ''}`}>
          <BarChart3 size={18} />
          <span>PAPER_TRADING</span>
        </Link>
        <Link to="/portfolio" className={`nav-item ${path === '/portfolio' ? 'active' : ''}`}>
          <Wallet size={18} />
          <span>PORTFOLIO_PNL</span>
        </Link>
      </nav>

      <div className="sidebar-footer">
        [SYS] ALL AGENTS NOMINAL
      </div>
    </div>
  );
}

function App() {
  const [ticker, setTicker] = useState<string>("SYSTEM_IDLE: AWAITING_INPUT");

  useEffect(() => {
    const updateTicker = async () => {
      try {
        const data = await apiRequest<{ signals_today: number; healthy_agent_count: number; total_agent_count: number; dag_memory: { node_count: number } }>('/api/dashboard/overview');
        const msg = `[SIGNALS_TODAY]: ${data.signals_today} | [HEALTHY_AGENTS]: ${data.healthy_agent_count}/${data.total_agent_count} | [DAG_SIZE]: ${data.dag_memory.node_count} nodes`;
        setTicker(msg);
      } catch {
        setTicker("SYS_ERROR: API_OFFLINE");
      }
    };
    updateTicker();
    const interval = setInterval(updateTicker, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <header className="top-bar">
             <div className="ticker-wrapper !bg-[#ff9d00]/5 !border-[#ff9d00]/20">
               <div className="ticker-label !text-[#ff9d00]">LIVE_TELEMETRY</div>
               <div className="ticker-text !text-white/80">{ticker}</div>
             </div>
             <div className="text-slate-700 font-mono text-[10px] tracking-widest">{new Date().toISOString().split('T')[0]} // SECURE_NODE</div>
          </header>
          <div className="page-container">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/research" element={<ResearchHub />} />
                <Route path="/backtest" element={<Backtest />} />
                <Route path="/data" element={<DataSources />} />
                <Route path="/code" element={<CodeViewer />} />
                <Route path="/ev" element={<MasterDashboard />} />
                <Route path="/costs" element={<Costs />} />
                <Route path="/council" element={<Council />} />
                <Route path="/memory" element={<MemoryDAG />} />
                <Route path="/attribution" element={<Attribution />} />
                <Route path="/orchestration" element={<Orchestration />} />
                <Route path="/settings" element={<SettingsView />} />
                <Route path="/failure-ledger" element={<FailureLedger />} />
                <Route path="/research-lab" element={<ResearchLab />} />
                <Route path="/paper" element={<PaperTrading />} />
                <Route path="/portfolio" element={<Portfolio />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
