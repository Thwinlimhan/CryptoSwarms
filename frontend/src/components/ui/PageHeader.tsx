import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
}

const PageHeader: React.FC<PageHeaderProps> = ({ 
  title, 
  description, 
  actions, 
  breadcrumbs 
}) => {
  return (
    <div className="mb-6 flex flex-col gap-0 border-b border-slate-900 pb-2">
      <div className="flex-1">
        {breadcrumbs && (
          <nav className="flex mb-1 text-[8px] font-bold text-slate-700 uppercase tracking-[0.4em]">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <span className="mx-2 text-slate-900">::</span>}
                {crumb.href ? (
                  <a href={crumb.href} className="hover:text-amber-500 transition-colors">{crumb.label}</a>
                ) : (
                  <span>{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        <h1 className="text-2xl font-black tracking-[0.2em] text-[#ff9d00] uppercase">
          {title}
        </h1>
        <div className="flex flex-col mt-0.5">
          {description && (
            <p className="text-slate-600 font-mono text-[9px] uppercase tracking-[0.15em]">
              {description}
            </p>
          )}
          <div className="text-[#ff9d00] font-mono text-[9px] uppercase tracking-[0.1em] mt-0.5 opacity-80">
            SWARM_ONLINE // AGENTS_NOMINAL
          </div>
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 mt-2">{actions}</div>}
    </div>
  );
};

export default PageHeader;
