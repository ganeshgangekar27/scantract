import { FileText } from 'lucide-react';

export interface LogoProps {
  showText?: boolean;
  className?: string;
}

export function Logo({ showText = true, className = '' }: LogoProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center">
        <FileText className="w-5 h-5 text-white" />
      </div>
      {showText && (
        <span className="text-xl font-bold bg-gradient-to-r from-primary to-primary-dark bg-clip-text text-transparent">
          ScanTract
        </span>
      )}
    </div>
  );
}
