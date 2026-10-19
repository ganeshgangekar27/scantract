import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo, PasswordStrength } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ShieldCheck, FileSearch, MessageSquare } from 'lucide-react';

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
  const shouldReduceMotion = useReducedMotion();
  
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

  const benefits = [
    { icon: ShieldCheck, text: 'Spot risky clauses' },
    { icon: FileSearch, text: 'Understand them in plain language' },
    { icon: MessageSquare, text: "Know what's missing" },
  ];
  
  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel - desktop only */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-700 via-blue-800 to-indigo-900 items-center justify-center p-12 relative overflow-hidden">
        {/* Richer background: grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />
        
        {/* Blurred glow orbs */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-64 h-64 bg-blue-400/20 rounded-full blur-3xl"
          animate={shouldReduceMotion ? {} : {
            x: [0, 30, 0],
            y: [0, -20, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          aria-hidden="true"
        />
        <motion.div
          className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-indigo-400/15 rounded-full blur-3xl"
          animate={shouldReduceMotion ? {} : {
            x: [0, -40, 0],
            y: [0, 30, 0],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          aria-hidden="true"
        />
        
        <div className="relative z-10 text-white max-w-md">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-3 text-center">ScanTract</h1>
            <p className="text-lg text-blue-100 text-center">
              AI contract risk analysis
            </p>
          </div>
          
          <div className="space-y-4 mt-12">
            {benefits.map((benefit, i) => {
              const Icon = benefit.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: shouldReduceMotion ? 0 : -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: shouldReduceMotion ? 0 : i * 0.1 }}
                  className="flex items-center gap-3 text-blue-50"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-base">{benefit.text}</span>
                </motion.div>
              );
            })}
          </div>

          {/* Call to action text */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-16 text-center"
          >
            <p className="text-xl text-blue-100 leading-relaxed">
              Know what you're signing<br />
              before you sign it.
            </p>
          </motion.div>
        </div>
      </div>
      
      {/* Right panel - form */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <motion.div
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          <Card className="p-8 shadow-xl">
            <div className="lg:hidden flex justify-center mb-6">
              <Logo />
            </div>
            
            <h2 className="text-2xl font-bold text-text-primary mb-2">Create an account</h2>
            <p className="text-text-secondary mb-6">Get started with ScanTract</p>
            
            <form onSubmit={handleSubmit} noValidate className="space-y-5">
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
        </motion.div>
      </div>
    </div>
  );
}
