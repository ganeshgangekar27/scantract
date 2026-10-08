import { useState } from 'react';
import type { InputHTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { Eye, EyeOff } from 'lucide-react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({ 
  label, 
  error, 
  hint, 
  type = 'text', 
  className,
  ...props 
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword && showPassword ? 'text' : type;
  
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          type={inputType}
          className={clsx(
            'w-full px-3 py-2 bg-surface border rounded-lg text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error ? 'border-severity-high' : 'border-border',
            isPassword && 'pr-10',
            className
          )}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-sm text-severity-high">{error}</p>
      )}
      {hint && !error && (
        <p className="mt-1 text-sm text-text-secondary">{hint}</p>
      )}
    </div>
  );
}
