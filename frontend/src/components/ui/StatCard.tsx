import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'primary' | 'success' | 'warning' | 'danger';
  subValue?: string;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  icon, 
  trend, 
  variant = 'primary',
  subValue
}) => {
  const variantColors = {
    primary: '#ff9d00',
    success: 'var(--accent-info)',
    warning: '#ff9d00',
    danger: 'var(--accent-alert)',
  };

  return (
    <div className="p-5 border border-slate-900 bg-black hover:border-slate-800 transition-colors flex flex-col justify-center min-h-[100px]">
      <div className="mb-2">
        <h3 className="text-[#ff9d00] text-[9px] font-bold uppercase tracking-[0.2em] opacity-60">{title}</h3>
      </div>
      <div className="flex flex-col">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black font-mono text-white tracking-widest uppercase">
            {value}
          </span>
          {trend && (
            <span className={`text-[10px] font-mono ${trend.isPositive ? 'text-green-500' : 'text-red-500'}`}>
              {trend.isPositive ? '+' : '-'}{Math.abs(trend.value)}%
            </span>
          )}
        </div>
        {subValue && (
          <span className="text-[9px] text-slate-600 mt-1 uppercase font-mono tracking-widest">
            {subValue}
          </span>
        )}
      </div>
    </div>
  );
};

export default StatCard;
