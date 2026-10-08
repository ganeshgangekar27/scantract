import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [demoLink, setDemoLink] = useState<string | null>(null);
  
  const { forgotPassword } = useAuth();
  const navigate = useNavigate();
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await forgotPassword(email);
      setSubmitted(true);
      if (response.demo_reset_link) {
        setDemoLink(response.demo_reset_link);
      }
      toast.success('Check your email for reset instructions');
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };
  
  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md p-8 text-center">
          <div className="flex justify-center mb-6">
            <Logo />
          </div>
          
          <h1 className="text-2xl font-bold text-text-primary mb-4">
            Check your email
          </h1>
          <p className="text-text-secondary mb-6">
            If an account exists with <strong>{email}</strong>, we've sent you a password reset link.
          </p>
          
          {demoLink && (
            <div className="mb-6 p-4 bg-severity-medium-bg border border-severity-medium-border rounded-lg text-left">
              <p className="text-sm font-medium mb-2">Demo Mode:</p>
              <a
                href={demoLink}
                className="text-sm text-primary underline break-all"
              >
                {demoLink}
              </a>
            </div>
          )}
          
          <Button onClick={() => navigate('/login')} variant="secondary">
            Back to login
          </Button>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md p-8">
        <div className="flex justify-center mb-6">
          <Logo />
        </div>
        
        <h1 className="text-2xl font-bold text-center text-text-primary mb-2">
          Forgot password?
        </h1>
        <p className="text-center text-text-secondary mb-6">
          Enter your email and we'll send you a reset link
        </p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          
          <Button type="submit" loading={loading} className="w-full">
            Send reset link
          </Button>
        </form>
        
        <p className="mt-6 text-center text-sm text-text-secondary">
          Remember your password?{' '}
          <button
            onClick={() => navigate('/login')}
            className="text-primary hover:underline font-medium"
          >
            Log in
          </button>
        </p>
      </Card>
    </div>
  );
}
