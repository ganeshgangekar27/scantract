import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setEmailError('');
    setPasswordError('');
    setLoading(true);
    
    try {
      await login(email, password);
      toast.success('Welcome back!');
      
      // Check for redirect path
      const redirectPath = sessionStorage.getItem('redirect_after_login') || '/dashboard';
      sessionStorage.removeItem('redirect_after_login');
      navigate(redirectPath);
    } catch (err) {
      if (err instanceof ApiError) {
        // Map error to specific field
        if (err.message.includes('No account found')) {
          setEmailError(err.message);
        } else if (err.message.includes('Incorrect password')) {
          setPasswordError(err.message);
        } else if (err.message.includes('Account is inactive')) {
          setEmailError(err.message);
        } else {
          toast.error(err.message);
        }
      } else if (err instanceof Error) {
        // Network or fetch errors
        if (err.message.includes('fetch') || err.message.includes('NetworkError') || err.message.includes('network')) {
          toast.error('Cannot reach the server. Please check your connection.');
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
  
  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel - desktop only */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-primary-dark items-center justify-center p-12 relative overflow-hidden">
        {/* Animated floating shapes */}
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
      
      {/* Right panel - form */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <Card className="w-full max-w-md p-8">
          <div className="lg:hidden flex justify-center mb-6">
            <Logo />
          </div>
          
          <h2 className="text-2xl font-bold text-text-primary mb-2">Log in to your account</h2>
          <p className="text-text-secondary mb-6">Welcome back! Please enter your details.</p>
          
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={emailError}
              placeholder="you@example.com"
              required
            />
            
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={passwordError}
              placeholder="••••••••"
              required
            />
            
            <div className="flex justify-end">
              <Link to="/forgot-password" className="text-sm text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            
            <Button type="submit" loading={loading} className="w-full">
              Log in
            </Button>
          </form>
          
          <p className="mt-6 text-center text-sm text-text-secondary">
            Don't have an account?{' '}
            <Link to="/signup" className="text-primary hover:underline font-medium">
              Sign up
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
