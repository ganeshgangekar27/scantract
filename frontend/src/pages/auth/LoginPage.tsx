import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Input, Button, Card, Logo } from '../../components/ui';
import { ApiError } from '../../lib/api';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ShieldCheck, FileSearch, MessageSquare } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [selectedClause, setSelectedClause] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [displayScore, setDisplayScore] = useState(0);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();

  // Auto-cycle clause selection
  useEffect(() => {
    if (hasInteracted || shouldReduceMotion) return;
    
    const interval = setInterval(() => {
      setSelectedClause((prev) => (prev + 1) % 3);
    }, 3000);
    
    return () => clearInterval(interval);
  }, [hasInteracted, shouldReduceMotion]);

  // Count-up animation for score
  useEffect(() => {
    if (shouldReduceMotion) {
      setDisplayScore(72);
      return;
    }
    
    let start = 0;
    const end = 72;
    const duration = 1000;
    const increment = end / (duration / 16);
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setDisplayScore(end);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(start));
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [shouldReduceMotion]);
  
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

  const benefits = [
    { icon: ShieldCheck, text: 'Spot risky clauses' },
    { icon: FileSearch, text: 'Understand them in plain language' },
    { icon: MessageSquare, text: "Know what's missing" },
  ];

  const clauses = [
    { 
      id: 0,
      name: 'Unlimited liability', 
      severity: 'High', 
      severityColor: 'red',
      explanation: 'Sample: This clause may expose you to financial risks beyond the contract value.'
    },
    { 
      id: 1,
      name: 'Auto-renewal', 
      severity: 'Medium', 
      severityColor: 'amber',
      explanation: 'Sample: Contract continues automatically unless canceled in advance.'
    },
    { 
      id: 2,
      name: 'Governing law', 
      severity: 'Low', 
      severityColor: 'green',
      explanation: 'Sample: Specifies jurisdiction for disputes, may require travel for legal matters.'
    },
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

          {/* Sample risk report mock card */}
          <div className="relative mt-16">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              whileHover={shouldReduceMotion ? {} : { y: -4 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="bg-white/95 backdrop-blur-sm rounded-lg shadow-2xl p-4"
              role="region"
              aria-label="Sample risk report preview"
              onMouseEnter={() => setHasInteracted(true)}
            >
              {/* Card header */}
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-800">Sample risk report</h3>
                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">
                  High risk
                </span>
              </div>

              {/* Clause rows - interactive buttons */}
              <div className="space-y-2 mb-3">
                {clauses.map((clause) => (
                  <button
                    key={clause.id}
                    type="button"
                    onClick={() => {
                      setSelectedClause(clause.id);
                      setHasInteracted(true);
                    }}
                    onFocus={() => setHasInteracted(true)}
                    className={`w-full flex items-center justify-between border-l-4 ${
                      clause.severityColor === 'red' ? 'border-red-500' :
                      clause.severityColor === 'amber' ? 'border-amber-500' :
                      'border-green-500'
                    } pl-2 py-1.5 rounded-r transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                      selectedClause === clause.id 
                        ? 'bg-blue-50' 
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <span className="text-xs text-gray-700 font-medium">{clause.name}</span>
                    <span className={`px-1.5 py-0.5 text-xs rounded ${
                      clause.severityColor === 'red' ? 'bg-red-50 text-red-600' :
                      clause.severityColor === 'amber' ? 'bg-amber-50 text-amber-600' :
                      'bg-green-50 text-green-600'
                    }`}>
                      {clause.severity}
                    </span>
                  </button>
                ))}
              </div>

              {/* Explanation box */}
              <motion.div
                key={selectedClause}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-gray-700"
              >
                {clauses[selectedClause].explanation}
              </motion.div>

              {/* Severity bar with animation and score */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">Risk score</span>
                  <span className="text-xs font-semibold text-gray-700">{displayScore} / 100</span>
                </div>
                <div className="flex h-1.5 rounded-full overflow-hidden bg-gray-200">
                  <motion.div
                    className="bg-red-500"
                    initial={{ width: 0 }}
                    animate={{ width: '33.33%' }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.8, delay: 0.5 }}
                  />
                  <motion.div
                    className="bg-amber-500"
                    initial={{ width: 0 }}
                    animate={{ width: '33.33%' }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.8, delay: 0.7 }}
                  />
                  <motion.div
                    className="bg-green-500"
                    initial={{ width: 0 }}
                    animate={{ width: '33.33%' }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.8, delay: 0.9 }}
                  />
                </div>
              </div>
            </motion.div>

            {/* Floating chip 1 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ 
                opacity: 1,
                y: shouldReduceMotion ? 0 : [0, -6, 0]
              }}
              transition={{
                opacity: { duration: 0.5, delay: 0.7 },
                y: shouldReduceMotion ? {} : { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }
              }}
              className="absolute -top-4 -right-4 bg-blue-500 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1.5 text-xs font-medium"
              aria-hidden="true"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Clause detected
            </motion.div>

            {/* Floating chip 2 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ 
                opacity: 1,
                y: shouldReduceMotion ? 0 : [0, -6, 0]
              }}
              transition={{
                opacity: { duration: 0.5, delay: 0.9 },
                y: shouldReduceMotion ? {} : { duration: 3, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }
              }}
              className="absolute -bottom-3 -left-6 bg-indigo-500 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1.5 text-xs font-medium"
              aria-hidden="true"
            >
              <FileSearch className="w-3.5 h-3.5" />
              Plain-language explanation
            </motion.div>

        
    
          </div>
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
            
            <h2 className="text-2xl font-bold text-text-primary mb-2">Log in to your account</h2>
            <p className="text-text-secondary mb-6">Welcome back! Please enter your details.</p>
            
            <form onSubmit={handleSubmit} noValidate className="space-y-5">
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
            <p className="mt-2 text-center text-xs text-text-secondary">
              Your contracts are private to your account.
            </p>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}