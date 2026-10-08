import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
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
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      toast.error('Login failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md p-8">
        <div className="flex justify-center mb-6">
          <Logo />
        </div>
        
        <h1 className="text-2xl font-bold text-center text-text-primary mb-2">
          Log in to your account
        </h1>
        <p className="text-center text-text-secondary mb-6">
          Welcome back! Please enter your details.
        </p>
        
        {error && (
          <div className="mb-4 p-3 bg-severity-high-bg border border-severity-high-border rounded-lg text-severity-high text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
          
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="text-sm text-primary hover:underline"
            >
              Forgot password?
            </button>
          </div>
          
          <Button type="submit" loading={loading} className="w-full">
            Log in
          </Button>
        </form>
        
        <p className="mt-6 text-center text-sm text-text-secondary">
          Don't have an account?{' '}
          <button
            onClick={() => navigate('/signup')}
            className="text-primary hover:underline font-medium"
          >
            Sign up
          </button>
        </p>
      </Card>
    </div>
  );
}
