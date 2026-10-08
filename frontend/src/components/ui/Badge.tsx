import type { HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';
import type { SeverityLevel } from '../../lib/severity';

export type BadgeVariant = 'severity' | 'status';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  severity?: SeverityLevel;
  status?: 'active' | 'pending' | 'completed';
  children: ReactNode;
}

export function Badge({ 
  variant = 'status', 
  severity, 
  status,
  children, 
  className,
  ...props 
}: BadgeProps) {
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  
  let variantClasses = '';
  
  if (variant === 'severity' && severity) {
    const severityMap = {
      high: 'text-severity-high bg-severity-high-bg border border-severity-high-border',
      medium: 'text-severity-medium bg-severity-medium-bg border border-severity-medium-border',
      low: 'text-severity-low bg-severity-low-bg border border-severity-low-border',
      safe: 'text-severity-safe bg-severity-safe-bg border border-severity-safe-border',
    };
    variantClasses = severityMap[severity];
  } else if (variant === 'status' && status) {
    const statusMap = {
      active: 'bg-green-100 text-green-800 border border-green-200',
      pending: 'bg-amber-100 text-amber-800 border border-amber-200',
      completed: 'bg-blue-100 text-blue-800 border border-blue-200',
    };
    variantClasses = statusMap[status];
  }
  
  return (
    <span className={clsx(baseClasses, variantClasses, className)} {...props}>
      {children}
    </span>
  );
}
