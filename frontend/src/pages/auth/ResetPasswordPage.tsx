import { useState, type FormEvent, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo, PasswordStrength } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!token) {
      toast.error('Invalid reset link');
      navigate('/login');
    }
  }, [token, navigate]);
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    setLoading(true);
    
    try {
      await resetPassword(token, password);
      toast.success('Password reset successfully!');
      navigate('/login');
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
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md p-8">
        <div className="flex justify-center mb-6">
          <Logo />
        </div>
        
        <h1 className="text-2xl font-bold text-center text-text-primary mb-2">
          Reset your password
        </h1>
        <p className="text-center text-text-secondary mb-6">
          Enter your new password below
        </p>
        
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
            <PasswordStrength password={password} />
          </div>
          
          <Button type="submit" loading={loading} className="w-full">
            Reset password
          </Button>
        </form>
      </Card>
    </div>
  );
}
