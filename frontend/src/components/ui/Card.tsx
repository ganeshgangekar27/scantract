import type { HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-surface border border-border rounded-lg shadow-sm',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
