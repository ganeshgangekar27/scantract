import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  children: ReactNode;
}

export function Button({ 
  variant = 'primary', 
  loading = false, 
  disabled,
  className,
  children,
  ...props 
}: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center px-4 py-2 rounded-lg font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variantClasses = {
    primary: 'bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-lg hover:-translate-y-0.5 active:scale-95 disabled:hover:shadow-none disabled:hover:translate-y-0',
    secondary: 'bg-surface border border-border text-text-primary hover:bg-gray-50 active:scale-95',
    ghost: 'text-text-primary hover:bg-gray-100 active:scale-95',
  };
  
  return (
    <button
      className={clsx(baseClasses, variantClasses[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {children}
    </button>
  );
}
