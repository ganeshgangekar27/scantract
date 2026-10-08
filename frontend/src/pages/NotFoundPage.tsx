import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui';
import { AlertCircle } from 'lucide-react';

export function NotFoundPage() {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-severity-high-bg flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-severity-high" />
          </div>
        </div>
        
        <h1 className="text-6xl font-bold text-text-primary mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-text-primary mb-2">Page not found</h2>
        <p className="text-text-secondary mb-8 max-w-sm">
          The page you're looking for doesn't exist or has been moved.
        </p>
        
        <div className="flex gap-4 justify-center">
          <Button onClick={() => navigate(-1)} variant="secondary">
            Go back
          </Button>
          <Button onClick={() => navigate('/dashboard')}>
            Go to dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
