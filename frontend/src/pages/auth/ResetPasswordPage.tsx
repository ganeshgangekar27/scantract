import { useState, type FormEvent, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo, PasswordStrength, ErrorState } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tokenError, setTokenError] = useState(false);
  
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!token) {
      setTokenError(true);
    }
  }, [token]);
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    
    setError('');
    setLoading(true);
    
    try {
      await resetPassword(token, password);
      toast.success('Password reset successfully!');
      navigate('/login');
    } catch (err) {
      if (err instanceof ApiError) {
        if (
          err.message.includes('expired') ||
          err.message.includes('already used') ||
          err.message.includes('Invalid')
        ) {
          setTokenError(true);
        } else {
          toast.error(err.message);
        }
      } else {
        toast.error('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };
  
  if (tokenError) {
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
            
            <ErrorState
              title="Invalid reset link"
              message="This password reset link is invalid, expired, or has already been used."
            />
            
            <div className="mt-6 space-y-3">
              <Button
                onClick={() => navigate('/forgot-password')}
                className="w-full"
              >
                Request a new link
              </Button>
              <Button
                onClick={() => navigate('/login')}
                variant="secondary"
                className="w-full"
              >
                Back to login
              </Button>
            </div>
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
          
          <h2 className="text-2xl font-bold text-text-primary mb-2">Reset your password</h2>
          <p className="text-text-secondary mb-6">Enter your new password below</p>
          
          {error && (
            <div className="mb-4 p-3 bg-severity-high-bg border border-severity-high-border rounded-lg text-severity-high text-sm">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                label="New password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                hint="At least 8 characters"
                required
              />
              {password && <PasswordStrength password={password} />}
            </div>
            
            <Input
              label="Confirm password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
            
            <Button type="submit" loading={loading} className="w-full">
              Reset password
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
