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
  Settings
} from 'lucide-react';
import './App.css';

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

function Sidebar() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
          <Network size={20} />
          SWARM_OS
        </h2>
        <div className="text-muted" style={{ fontSize: '0.7em', marginTop: '0.5rem' }}>v6.0.0-rc1 // SECURE</div>
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
        const res = await fetch('http://127.0.0.1:8000/api/dashboard/overview');
        const data = await res.json();
        const msg = `[SIGNALS_TODAY]: ${data.signals_today} | [HEALTHY_AGENTS]: ${data.healthy_agent_count}/${data.total_agent_count} | [DAG_SIZE]: ${data.dag_memory.node_count} nodes`;
        setTicker(msg);
      } catch (e) {
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
             <div className="ticker-wrapper">
               <div className="ticker-label">LIVE_TELEMETRY</div>
               <div className="ticker-text">{ticker}</div>
             </div>
             <div className="text-muted" style={{ fontSize: '0.8rem' }}>{new Date().toISOString().split('T')[0]} // SECURE_SOCKET</div>
          </header>
          <div className="page-container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/research" element={<ResearchHub />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/data" element={<DataSources />} />
              <Route path="/code" element={<CodeViewer />} />
              <Route path="/costs" element={<Costs />} />
              <Route path="/council" element={<Council />} />
              <Route path="/memory" element={<MemoryDAG />} />
              <Route path="/attribution" element={<Attribution />} />
              <Route path="/orchestration" element={<Orchestration />} />
              <Route path="/settings" element={<SettingsView />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
