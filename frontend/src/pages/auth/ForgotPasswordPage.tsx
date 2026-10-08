import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
      <div className="min-h-screen flex bg-background">
        <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-primary-dark items-center justify-center p-12 relative overflow-hidden">
          <div className="absolute top-20 left-20 w-32 h-32 bg-white/10 rounded-full animate-pulse" />
          <div className="absolute bottom-40 right-32 w-24 h-24 bg-white/10 rounded-full animate-pulse" style={{ animationDelay: '1s' }} />
          <div className="absolute top-1/2 right-20 w-40 h-40 bg-white/10 rounded-full animate-pulse" style={{ animationDelay: '2s' }} />
          
          <div className="relative z-10 text-white text-center max-w-md">
            <Logo showText={false} className="mb-8 mx-auto" />
            <h1 className="text-4xl font-bold mb-6">ScanTract</h1>
            <p className="text-xl leading-relaxed opacity-90">
              Know what you're signing<br />
              before you sign it.
            </p>
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
          <Card className="w-full max-w-md p-8">
            <div className="lg:hidden flex justify-center mb-6">
              <Logo />
            </div>
            
            <h2 className="text-2xl font-bold text-text-primary mb-4">Check your email</h2>
            <p className="text-text-secondary mb-6">
              If an account exists with that email, we've sent a password reset link.
            </p>
            
            {demoLink && (
              <Card className="mb-6 p-4 bg-severity-medium-bg border border-severity-medium-border">
                <p className="text-sm font-semibold text-text-primary mb-3">Demo mode: open reset link</p>
                <Button
                  onClick={() => window.location.href = demoLink}
                  variant="secondary"
                  className="w-full"
                >
                  Open reset link
                </Button>
              </Card>
            )}
            
            <Button onClick={() => navigate('/login')} variant="secondary" className="w-full">
              Back to login
            </Button>
          </Card>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen flex bg-background">
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-primary-dark items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute top-20 left-20 w-32 h-32 bg-white/10 rounded-full animate-pulse" />
        <div className="absolute bottom-40 right-32 w-24 h-24 bg-white/10 rounded-full animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 right-20 w-40 h-40 bg-white/10 rounded-full animate-pulse" style={{ animationDelay: '2s' }} />
        
        <div className="relative z-10 text-white text-center max-w-md">
          <Logo showText={false} className="mb-8 mx-auto" />
          <h1 className="text-4xl font-bold mb-6">ScanTract</h1>
          <p className="text-xl leading-relaxed opacity-90">
            Know what you're signing<br />
            before you sign it.
          </p>
        </div>
      </div>
      
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <Card className="w-full max-w-md p-8">
          <div className="lg:hidden flex justify-center mb-6">
            <Logo />
          </div>
          
          <h2 className="text-2xl font-bold text-text-primary mb-2">Forgot password?</h2>
          <p className="text-text-secondary mb-6">Enter your email and we'll send you a reset link</p>
          
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
            <Link to="/login" className="text-primary hover:underline font-medium">
              Log in
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
