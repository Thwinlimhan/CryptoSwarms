import React from 'react';

interface FeedItemProps {
  title: string;
  subtitle?: string;
  timestamp: string;
  icon?: React.ReactNode;
  variant?: 'info' | 'success' | 'warning' | 'danger';
}

export const FeedItem: React.FC<FeedItemProps> = ({ 
  title, 
  subtitle, 
  timestamp, 
  icon,
  variant = 'info'
}) => {
  const borderStyles = {
    info: 'border-blue-500/30',
    success: 'border-green-500/30',
    warning: 'border-yellow-500/30',
    danger: 'border-red-500/30',
  };

  return (
    <div className={`p-4 mb-3 rounded-lg border-l-4 bg-slate-800/30 border-y border-r border-slate-700/50 ${borderStyles[variant]}`}>
      <div className="flex justify-between items-start mb-1">
        <span className="text-sm font-semibold text-white">{title}</span>
        <span className="text-[10px] text-slate-500 font-mono uppercase">{timestamp}</span>
      </div>
      {subtitle && <p className="text-xs text-slate-400 leading-relaxed">{subtitle}</p>}
      {icon && <div className="mt-2 text-xs">{icon}</div>}
    </div>
  );
};

interface FeedListProps {
  children: React.ReactNode;
  title?: string;
  maxHeight?: string;
}

export const FeedList: React.FC<FeedListProps> = ({ children, title, maxHeight = '400px' }) => {
  return (
    <div className="flex flex-col">
      {title && (
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">
          {title}
        </h4>
      )}
      <div className="overflow-y-auto pr-2 custom-scrollbar" style={{ maxHeight }}>
        {children}
      </div>
    </div>
  );
};
