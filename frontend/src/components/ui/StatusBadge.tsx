import React from 'react';

type StatusVariant = 'success' | 'warning' | 'error' | 'info' | 'active';

interface StatusBadgeProps {
  status: string;
  variant?: StatusVariant;
  pulse?: boolean;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  variant = 'info', 
  pulse = false 
}) => {
  const variantStyles = {
    success: 'text-green-500',
    warning: 'text-amber-500',
    error: 'text-red-500',
    info: 'text-amber-500',
    active: 'text-amber-500',
  };

  return (
    <span className={`inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest ${variantStyles[variant]}`}>
      <span className="opacity-50">[</span>
      {pulse && (
        <span className="flex h-1.5 w-1.5 rounded-full bg-current animate-pulse mr-1" />
      )}
      <span className="font-bold">{status}</span>
      <span className="opacity-50">]</span>
    </span>
  );
};

export default StatusBadge;
