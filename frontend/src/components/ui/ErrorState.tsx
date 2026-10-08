import { AlertCircle } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 mb-4 rounded-full bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
        <AlertCircle className="w-8 h-8 text-severity-high" />
      </div>
      <h3 className="text-lg font-semibold text-text-primary mb-2">Something went wrong</h3>
      <p className="text-text-secondary max-w-sm mb-6">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">Try again</Button>
      )}
    </div>
  );
}
