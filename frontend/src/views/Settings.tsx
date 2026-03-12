import { Settings, Shield, Cpu, Database, Palette, Key, Zap } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function SettingsView() {
  const [theme, setTheme] = useState(localStorage.getItem('swarm-theme') || 'green');
  const [keys, setKeys] = useState(() => {
    const saved = localStorage.getItem('swarm-keys');
    return saved ? JSON.parse(saved) : { openai: '', anthropic: '', exchange: '' };
  });
  const [routing, setRouting] = useState(() => {
    const saved = localStorage.getItem('swarm-routing');
    return saved ? JSON.parse(saved) : { research: 'claude-3-5-sonnet', execution: 'gpt-4o', summary: 'gpt-3.5-turbo' };
  });

  const themes = {
    green: { primary: '#00ff41', secondary: '#008f11', glow: 'rgba(0, 255, 65, 0.5)' },
    amber: { primary: '#ffb000', secondary: '#9c6b00', glow: 'rgba(255, 176, 0, 0.5)' },
    blue: { primary: '#00e5ff', secondary: '#008ba3', glow: 'rgba(0, 229, 255, 0.5)' },
    red: { primary: '#ff003c', secondary: '#9c0024', glow: 'rgba(255, 0, 60, 0.5)' },
    purple: { primary: '#a855f7', secondary: '#7e22ce', glow: 'rgba(168, 85, 247, 0.5)' },
    pink: { primary: '#ec4899', secondary: '#be185d', glow: 'rgba(236, 72, 153, 0.5)' },
    cyan: { primary: '#06b6d4', secondary: '#0891b2', glow: 'rgba(6, 182, 212, 0.5)' },
    gold: { primary: '#fbbf24', secondary: '#d97706', glow: 'rgba(251, 191, 36, 0.5)' },
  };

  useEffect(() => {
    const t = themes[theme as keyof typeof themes] || themes.green;
    document.documentElement.style.setProperty('--text-primary', t.primary);
    document.documentElement.style.setProperty('--text-secondary', t.secondary);
    document.documentElement.style.setProperty('--text-primary-glow', t.glow);
    localStorage.setItem('swarm-theme', theme);
  }, [theme]);

  const saveKeys = () => {
    localStorage.setItem('swarm-keys', JSON.stringify(keys));
    alert('KEYS_SECURED_IN_LOCAL_STORE');
  };

  const saveRouting = () => {
    localStorage.setItem('swarm-routing', JSON.stringify(routing));
    alert('ROUTING_POLICIES_UPDATED');
  };

  return (
    <div className="view-container">
      <header className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Settings className="text-primary" size={24} />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem' }}>SYSTEM_SETTINGS</h1>
            <div className="text-muted" style={{ fontSize: '0.8rem' }}>CONFIGURATION // SECURITY // THEME</div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-2">
        {/* Theme Selection */}
        <div className="border-box">
          <h3 style={{ margin: '0 0 1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Palette size={18} /> THEME_PERSONALITY
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            {Object.keys(themes).map((t) => (
              <button 
                key={t}
                onClick={() => setTheme(t)}
                style={{ 
                  borderColor: theme === t ? 'var(--text-primary)' : 'var(--text-muted)',
                  background: theme === t ? 'rgba(255,255,255,0.05)' : 'transparent',
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <div style={{ 
                  width: 24, height: 24, 
                  borderRadius: '50%', 
                  background: `radial-gradient(circle at 30% 30%, ${themes[t as keyof typeof themes].primary}, ${themes[t as keyof typeof themes].secondary})`,
                  boxShadow: `0 0 15px ${themes[t as keyof typeof themes].glow}`
                }}></div>
                <span style={{ fontSize: '0.65rem', fontWeight: 'bold' }}>{t.toUpperCase()}</span>
              </button>
            ))}
          </div>
        </div>

        {/* API Keys */}
        <div className="border-box">
          <h3 style={{ margin: '0 0 1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Key size={18} /> PROVIDER_SECRET_KEYS
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>OPENAI_API_KEY</label>
              <input 
                type="password" 
                value={keys.openai} 
                onChange={(e) => setKeys({...keys, openai: e.target.value})}
                placeholder="sk-..."
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ANTHROPIC_API_KEY</label>
              <input 
                type="password" 
                value={keys.anthropic} 
                onChange={(e) => setKeys({...keys, anthropic: e.target.value})}
                placeholder="sk-ant-..."
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>EXCHANGE_API_KEY</label>
              <input 
                type="password" 
                value={keys.exchange} 
                onChange={(e) => setKeys({...keys, exchange: e.target.value})}
              />
            </div>
            <button onClick={saveKeys} style={{ marginTop: '0.5rem' }}>VALIDATE_AND_SAVE</button>
          </div>
        </div>

        {/* Model Routing */}
        <div className="border-box">
          <h3 style={{ margin: '0 0 1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={18} /> MODEL_ROUTING_TOPOLOGY
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem' }}>RESEARCH_SWARM</span>
              <select 
                value={routing.research} 
                onChange={(e) => setRouting({...routing, research: e.target.value})}
                style={{ width: '200px' }}
              >
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="deepseek-v3">DeepSeek V3</option>
              </select>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem' }}>EXECUTION_ENGINE</span>
              <select 
                value={routing.execution} 
                onChange={(e) => setRouting({...routing, execution: e.target.value})}
                style={{ width: '200px' }}
              >
                <option value="gpt-4o">GPT-4o</option>
                <option value="claude-3-opus">Claude 3 Opus</option>
                <option value="gemini-1-5-pro">Gemini 1.5 Pro</option>
              </select>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem' }}>SUMMARY_AGENT</span>
              <select 
                value={routing.summary} 
                onChange={(e) => setRouting({...routing, summary: e.target.value})}
                style={{ width: '200px' }}
              >
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="claude-3-haiku">Claude 3 Haiku</option>
                <option value="llama-3-8b">Llama 3 8B</option>
              </select>
            </div>
            <button onClick={saveRouting} style={{ marginTop: '1rem' }}>DEPLOY_ROUTING_MAP</button>
          </div>
        </div>

        {/* Security / Guardian */}
        <div className="border-box" style={{ borderColor: 'var(--accent-alert)' }}>
          <h3 style={{ margin: '0 0 1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-alert)' }}>
            <Shield size={18} /> GUARDIAN_OVERRIDE
          </h3>
          <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '1.5rem' }}>
            FORCE_MANDATORY_VALIDATION_ON_ALL_TRADES. EXCEEDS_BUDGET_GUARD_V2.
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
             <div style={{ 
               width: 50, height: 26, 
               background: 'rgba(255,0,60,0.1)', 
               border: '1px solid var(--accent-alert)',
               padding: 3,
               borderRadius: 13,
               cursor: 'pointer',
               display: 'flex',
               justifyContent: 'flex-end'
             }}>
               <div style={{ width: 20, height: 20, background: 'var(--accent-alert)', borderRadius: '50%' }}></div>
             </div>
             <span style={{ fontSize: '0.8rem', color: 'var(--accent-alert)' }}>ENFORCE_MAX_RISK</span>
          </div>
          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
             <button style={{ flex: 1, borderColor: 'var(--accent-alert)', color: 'var(--accent-alert)' }}>PURGE_ALL_KEYS</button>
             <button style={{ flex: 1 }}>EXPORT_CONFIG</button>
          </div>
        </div>
      </div>
    </div>
  );
}
