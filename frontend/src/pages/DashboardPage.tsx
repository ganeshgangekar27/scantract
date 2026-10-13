import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  FileText, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Upload,
  ChevronRight
} from 'lucide-react';
import { AppShell } from '../components/AppShell';
import { Button, Card } from '../components/ui';
import { useAuth } from '../auth/AuthContext';
import { listContracts } from '../lib/api';
import type { ContractListItem } from '../lib/types';

interface Stats {
  total: number;
  completed: number;
  processing: number;
  failed: number;
}

interface StatusMixData {
  completed: number;
  inProgress: number;
  failed: number;
}

const DONUT_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#10b981',
  none: '#6b7280',
  completed: '#10b981',
  processing: '#f59e0b',
  failed: '#ef4444',
  inProgress: '#3b82f6',
};

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, completed: 0, processing: 0, failed: 0 });
  const [statusMix, setStatusMix] = useState<StatusMixData>({ completed: 0, inProgress: 0, failed: 0 });
  
  const firstName = user?.full_name.split(' ')[0] || 'there';
  
  useEffect(() => {
    loadDashboardData();
  }, []);
  
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const allContracts = await listContracts();
      const userContracts = allContracts.filter(c => !c.is_sample);
      const samples = allContracts.filter(c => c.is_sample);
      
      setContracts([...userContracts, ...samples]);
      
      // Calculate stats (exclude samples)
      const newStats: Stats = {
        total: userContracts.length,
        completed: userContracts.filter(c => c.processing_status === 'completed').length,
        processing: userContracts.filter(c => c.processing_status === 'processing' || c.processing_status === 'uploaded').length,
        failed: userContracts.filter(c => c.processing_status === 'failed').length,
      };
      setStats(newStats);
      
      // Calculate status mix for status distribution chart
      const newStatusMix: StatusMixData = {
        completed: userContracts.filter(c => c.processing_status === 'completed').length,
        inProgress: userContracts.filter(c => c.processing_status === 'processing' || c.processing_status === 'uploaded').length,
        failed: userContracts.filter(c => c.processing_status === 'failed').length,
      };
      setStatusMix(newStatusMix);
      
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      setLoading(false);
    }
  };
  
  const getRelativeTime = (isoDate: string): string => {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };
  
  const getStatusBadge = (status: ContractListItem['processing_status']) => {
    const variants = {
      completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      processing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      uploaded: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };
    
    return (
      <span className={`text-xs px-2 py-1 rounded-full font-medium ${variants[status]}`}>
        {status === 'uploaded' ? 'Queued' : status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };
  
  const calculatePercentages = (data: StatusMixData): { label: string; count: number; percent: number; color: string }[] => {
    const total = data.completed + data.inProgress + data.failed;
    if (total === 0) return [];

    const items = [
      { label: 'Completed', count: data.completed, color: DONUT_COLORS.completed },
      { label: 'In progress', count: data.inProgress, color: DONUT_COLORS.inProgress },
      { label: 'Failed', count: data.failed, color: DONUT_COLORS.failed },
    ];

    // Calculate raw percentages
    const rawPercentages = items.map(item => ({
      ...item,
      rawPercent: (item.count / total) * 100,
      percent: 0,
    }));

    // Round down and calculate remainder
    let sum = 0;
    rawPercentages.forEach(item => {
      item.percent = Math.floor(item.rawPercent);
      sum += item.percent;
    });

    // Distribute remainder using largest remainder method
    const remainder = 100 - sum;
    if (remainder > 0) {
      const withRemainders = rawPercentages
        .map((item, idx) => ({ idx, remainder: item.rawPercent - item.percent }))
        .sort((a, b) => b.remainder - a.remainder);

      for (let i = 0; i < remainder; i++) {
        rawPercentages[withRemainders[i].idx].percent += 1;
      }
    }

    return rawPercentages;
  };

  const renderStatusDonut = (data: StatusMixData) => {
    const total = data.completed + data.inProgress + data.failed;
    if (total === 0) {
      return (
        <div className="text-center py-8 text-text-secondary">
          No contracts yet
        </div>
      );
    }

    const items = calculatePercentages(data);
    let currentAngle = -90;
    const segments: { angle: number; percent: number; color: string; label: string }[] = [];

    items.forEach(item => {
      if (item.count > 0) {
        segments.push({
          angle: currentAngle,
          percent: item.percent,
          color: item.color,
          label: item.label,
        });
        currentAngle += (item.percent / 100) * 360;
      }
    });

    return (
      <div className="flex flex-col items-center">
        <div className="relative">
          <svg viewBox="0 0 100 100" className="w-32 h-32" aria-label={`Status distribution: ${items.map(i => `${i.label} ${i.percent}%`).join(', ')}`}>
            <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="20" className="dark:stroke-gray-700" />
            {segments.map((seg, idx) => {
              const startAngle = (seg.angle * Math.PI) / 180;
              const endAngle = ((seg.angle + (seg.percent / 100) * 360) * Math.PI) / 180;
              const largeArc = seg.percent > 50 ? 1 : 0;

              const x1 = 50 + 40 * Math.cos(startAngle);
              const y1 = 50 + 40 * Math.sin(startAngle);
              const x2 = 50 + 40 * Math.cos(endAngle);
              const y2 = 50 + 40 * Math.sin(endAngle);

              return (
                <path
                  key={idx}
                  d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
                  fill={seg.color}
                  opacity="0.8"
                />
              );
            })}
            <circle cx="50" cy="50" r="25" fill="white" className="dark:fill-gray-900" />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-text-primary">{`${total} total`}</div>
            </div>
          </div>
        </div>
        <div className="mt-4 w-full space-y-2">
          {items.map(item => (
            <div key={item.label} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-text-secondary">{item.label}</span>
              </div>
              <span className="text-text-primary font-medium">
                {item.count} ({item.percent}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  if (loading) {
    return (
      <AppShell title="Dashboard">
        <div className="space-y-6">
          <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
            ))}
          </div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
        </div>
      </AppShell>
    );
  }
  
  if (error) {
    return (
      <AppShell title="Dashboard">
        <Card className="p-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">Failed to load dashboard</h2>
          <p className="text-text-secondary mb-4">{error}</p>
          <Button onClick={loadDashboardData}>Retry</Button>
        </Card>
      </AppShell>
    );
  }
  
  const userContracts = contracts.filter(c => !c.is_sample);
  const recentContracts = userContracts.slice(0, 5);
  const sampleContracts = contracts.filter(c => c.is_sample);
  
  if (userContracts.length === 0) {
    return (
      <AppShell title="Dashboard">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mx-auto"
        >
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            Welcome, {firstName}! 👋
          </h1>
          <p className="text-text-secondary mb-8">
            Let's analyze your first contract for potential risks and missing clauses.
          </p>
          
          <Card className="p-8 text-center mb-6">
            <Upload className="w-16 h-16 text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-text-primary mb-2">
              Analyze a new contract
            </h2>
            <p className="text-text-secondary mb-6">
              Upload a rental or freelance contract to get AI-powered risk analysis
            </p>
            <Button onClick={() => navigate('/upload')}>
              Upload Contract
            </Button>
          </Card>
          
          {sampleContracts.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                Try a sample contract
              </h3>
              <div className="space-y-2">
                {sampleContracts.slice(0, 3).map((contract) => (
                  <button
                    key={contract.contract_id}
                    onClick={() => navigate(`/contracts/${contract.contract_id}`)}
                    className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-text-secondary" />
                      <span className="text-text-primary font-medium">{contract.filename}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                        Sample
                      </span>
                    </div>
                    <ChevronRight className="w-5 h-5 text-text-secondary" />
                  </button>
                ))}
              </div>
            </Card>
          )}
        </motion.div>
      </AppShell>
    );
  }
  
  return (
    <AppShell title="Dashboard">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-6"
      >
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            Welcome back, {firstName}! 👋
          </h1>
          <p className="text-text-secondary">
            Here's an overview of your contract analyses
          </p>
        </div>
        
        {/* Stats cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-secondary text-sm">Total analyses</span>
                <FileText className="w-5 h-5 text-blue-500" />
              </div>
              <div className="text-3xl font-bold text-text-primary">{stats.total}</div>
            </Card>
          </motion.div>
          
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-secondary text-sm">Completed</span>
                <CheckCircle className="w-5 h-5 text-green-500" />
              </div>
              <div className="text-3xl font-bold text-text-primary">{stats.completed}</div>
            </Card>
          </motion.div>
          
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-secondary text-sm">In progress</span>
                <Clock className="w-5 h-5 text-yellow-500" />
              </div>
              <div className="text-3xl font-bold text-text-primary">{stats.processing}</div>
            </Card>
          </motion.div>
          
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-secondary text-sm">Failed</span>
                <AlertCircle className="w-5 h-5 text-red-500" />
              </div>
              <div className="text-3xl font-bold text-text-primary">{stats.failed}</div>
            </Card>
          </motion.div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent contracts */}
          <div className="lg:col-span-2">
            <Card className="p-6">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Recent contracts</h2>
              <div className="space-y-3">
                {recentContracts.map((contract) => (
                  <button
                    key={contract.contract_id}
                    onClick={() => {
                      if (contract.processing_status === 'completed') {
                        navigate(`/contracts/${contract.contract_id}`);
                      }
                    }}
                    disabled={contract.processing_status !== 'completed'}
                    className="w-full flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-text-secondary flex-shrink-0" />
                        <span className="text-text-primary font-medium truncate">{contract.filename}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-text-secondary">
                        <span>{getRelativeTime(contract.uploaded_at)}</span>
                        <span>•</span>
                        {getStatusBadge(contract.processing_status)}
                      </div>
                    </div>
                    {contract.processing_status === 'completed' && (
                      <ChevronRight className="w-5 h-5 text-text-secondary flex-shrink-0 ml-2" />
                    )}
                  </button>
                ))}
              </div>
            </Card>
          </div>
          
          {/* Status donut + Upload CTA */}
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Status mix</h2>
              {renderStatusDonut(statusMix)}
            </Card>
            
            <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
              <Upload className="w-8 h-8 text-primary mb-3" />
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                Analyze a new contract
              </h3>
              <p className="text-sm text-text-secondary mb-4">
                Upload another contract for AI-powered risk analysis
              </p>
              <Button onClick={() => navigate('/upload')} variant="primary" className="w-full">
                Upload Contract
              </Button>
            </Card>
          </div>
        </div>
        
        {/* Sample contracts */}
        {sampleContracts.length > 0 && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold text-text-primary mb-4">Try a sample contract</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {sampleContracts.slice(0, 3).map((contract) => (
                <button
                  key={contract.contract_id}
                  onClick={() => navigate(`/contracts/${contract.contract_id}`)}
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-all text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="w-5 h-5 text-text-secondary flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="text-text-primary font-medium truncate">{contract.filename}</div>
                      <div className="text-xs text-text-secondary">Sample</div>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-text-secondary flex-shrink-0" />
                </button>
              ))}
            </div>
          </Card>
        )}
      </motion.div>
    </AppShell>
  );
}
