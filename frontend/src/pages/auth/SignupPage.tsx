import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo, PasswordStrength } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';

export function SignupPage() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  
  const { register } = useAuth();
  const navigate = useNavigate();
  
  const validateEmail = (email: string): string => {
    if (!email) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email';
    return '';
  };
  
  const validatePassword = (password: string): string => {
    if (!password) return 'Password is required';
    if (password.length < 8) return 'Password must be at least 8 characters';
    return '';
  };
  
  const validateConfirmPassword = (confirm: string, password: string): string => {
    if (!confirm) return 'Please confirm your password';
    if (confirm !== password) return 'Passwords do not match';
    return '';
  };
  
  const handleBlur = (field: string) => {
    setTouched({ ...touched, [field]: true });
    
    const newErrors = { ...errors };
    if (field === 'fullName' && !fullName) {
      newErrors.fullName = 'Full name is required';
    } else if (field === 'fullName') {
      delete newErrors.fullName;
    }
    
    if (field === 'email') {
      const error = validateEmail(email);
      if (error) newErrors.email = error;
      else delete newErrors.email;
    }
    
    if (field === 'password') {
      const error = validatePassword(password);
      if (error) newErrors.password = error;
      else delete newErrors.password;
    }
    
    if (field === 'confirmPassword' || (field === 'password' && confirmPassword)) {
      const error = validateConfirmPassword(confirmPassword, password);
      if (error) newErrors.confirmPassword = error;
      else delete newErrors.confirmPassword;
    }
    
    setErrors(newErrors);
  };
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    // Validate all fields
    const newErrors: Record<string, string> = {};
    if (!fullName) newErrors.fullName = 'Full name is required';
    
    const emailError = validateEmail(email);
    if (emailError) newErrors.email = emailError;
    
    const passwordError = validatePassword(password);
    if (passwordError) newErrors.password = passwordError;
    
    const confirmError = validateConfirmPassword(confirmPassword, password);
    if (confirmError) newErrors.confirmPassword = confirmError;
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setTouched({ fullName: true, email: true, password: true, confirmPassword: true });
      return;
    }
    
    setLoading(true);
    setErrors({});
    
    try {
      await register(email, password, fullName);
      toast.success('Account created successfully!');
      navigate('/dashboard');
    } catch (err) {
      if (err instanceof ApiError) {
        // Handle duplicate email error
        if (err.message.includes('already exists')) {
          setErrors({ email: err.message });
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
          
          <h2 className="text-2xl font-bold text-text-primary mb-2">Create an account</h2>
          <p className="text-text-secondary mb-6">Get started with ScanTract</p>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              onBlur={() => handleBlur('fullName')}
              error={touched.fullName ? errors.fullName : ''}
              placeholder="John Doe"
              required
            />
            
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => handleBlur('email')}
              error={touched.email ? errors.email : ''}
              placeholder="you@example.com"
              required
            />
            
            <div>
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => handleBlur('password')}
                error={touched.password ? errors.password : ''}
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
              onBlur={() => handleBlur('confirmPassword')}
              error={touched.confirmPassword ? errors.confirmPassword : ''}
              placeholder="••••••••"
              required
            />
            
            <Button type="submit" loading={loading} className="w-full">
              Create account
            </Button>
          </form>
          
          <p className="mt-6 text-center text-sm text-text-secondary">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              Log in
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
