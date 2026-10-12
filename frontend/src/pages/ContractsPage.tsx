import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText,
  Search,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  Trash2,
  RotateCcw,
} from 'lucide-react';
import { AppShell } from '../components/AppShell';
import { Button, Card } from '../components/ui';
import { listContracts, deleteContract, retryContract } from '../lib/api';
import type { ContractListItem, ProcessingStatus } from '../lib/types';
import { toast } from 'sonner';

type TabType = 'my-contracts' | 'samples';
type StatusFilter = 'all' | 'completed' | 'processing' | 'failed';

export function ContractsPage() {
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('my-contracts');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  
  useEffect(() => {
    loadContracts();
  }, []);
  
  const loadContracts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listContracts();
      setContracts(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contracts');
      setLoading(false);
    }
  };
  
  const getStatusBadge = (status: ProcessingStatus) => {
    const variants = {
      completed: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-800 dark:text-green-400', icon: CheckCircle },
      processing: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-800 dark:text-yellow-400', icon: Clock },
      uploaded: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-800 dark:text-blue-400', icon: Clock },
      failed: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-800 dark:text-red-400', icon: XCircle },
    };
    
    const variant = variants[status];
    const Icon = variant.icon;
    const label = status === 'uploaded' ? 'Queued' : status.charAt(0).toUpperCase() + status.slice(1);
    
    return (
      <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-medium ${variant.bg} ${variant.text}`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };
  
  const formatDate = (isoDate: string): string => {
    return new Date(isoDate).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  const handleRowClick = (contract: ContractListItem) => {
    if (contract.processing_status === 'completed') {
      navigate(`/contracts/${contract.contract_id}`);
    }
  };
  
  const handleDelete = async (contractId: number) => {
    try {
      setActionLoading(contractId);
      setActionError(null);
      await deleteContract(contractId);
      toast.success('Contract deleted successfully');
      setDeleteConfirmId(null);
      await loadContracts();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete contract';
      setActionError(message);
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };
  
  const handleRetry = async (contractId: number) => {
    try {
      setActionLoading(contractId);
      setActionError(null);
      await retryContract(contractId);
      toast.success('Contract requeued for processing');
      await loadContracts();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to retry contract';
      setActionError(message);
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  };
  
  // Filter contracts
  const filteredContracts = contracts
    .filter((c) => (activeTab === 'my-contracts' ? !c.is_sample : c.is_sample))
    .filter((c) => c.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    .filter((c) => {
      if (statusFilter === 'all') return true;
      if (statusFilter === 'processing') return c.processing_status === 'processing' || c.processing_status === 'uploaded';
      return c.processing_status === statusFilter;
    })
    .sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime());
  
  const statusCounts = {
    all: contracts.filter(c => activeTab === 'my-contracts' ? !c.is_sample : c.is_sample).length,
    completed: contracts.filter(c => c.processing_status === 'completed' && (activeTab === 'my-contracts' ? !c.is_sample : c.is_sample)).length,
    processing: contracts.filter(c => (c.processing_status === 'processing' || c.processing_status === 'uploaded') && (activeTab === 'my-contracts' ? !c.is_sample : c.is_sample)).length,
    failed: contracts.filter(c => c.processing_status === 'failed' && (activeTab === 'my-contracts' ? !c.is_sample : c.is_sample)).length,
  };
  
  if (loading) {
    return (
      <AppShell title="My Contracts">
        <div className="space-y-4">
          <div className="h-10 w-64 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          <div className="h-12 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          ))}
        </div>
      </AppShell>
    );
  }
  
  if (error) {
    return (
      <AppShell title="My Contracts">
        <Card className="p-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">Failed to load contracts</h2>
          <p className="text-text-secondary mb-4">{error}</p>
          <Button onClick={loadContracts}>Retry</Button>
        </Card>
      </AppShell>
    );
  }
  
  const userContracts = contracts.filter(c => !c.is_sample);
  
  if (userContracts.length === 0 && activeTab === 'my-contracts') {
    return (
      <AppShell title="My Contracts">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mx-auto"
        >
          <Card className="p-8 text-center">
            <FileText className="w-16 h-16 text-text-secondary mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-text-primary mb-2">No contracts yet</h2>
            <p className="text-text-secondary mb-6">
              Upload your first contract to start analyzing for risks and missing clauses.
            </p>
            <Button onClick={() => navigate('/upload')}>
              Upload Contract
            </Button>
          </Card>
        </motion.div>
      </AppShell>
    );
  }
  
  return (
    <AppShell title="My Contracts">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-4"
      >
        {/* Tabs */}
        <div className="flex gap-4 border-b border-border">
          <button
            onClick={() => setActiveTab('my-contracts')}
            className={`pb-2 px-1 font-medium transition-colors border-b-2 ${
              activeTab === 'my-contracts'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            My Contracts ({userContracts.length})
          </button>
          <button
            onClick={() => setActiveTab('samples')}
            className={`pb-2 px-1 font-medium transition-colors border-b-2 ${
              activeTab === 'samples'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            Samples ({contracts.filter(c => c.is_sample).length})
          </button>
        </div>
        
        {/* Search and filters */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-secondary" />
            <input
              type="text"
              placeholder="Search contracts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          
          <div className="flex gap-2 overflow-x-auto">
            {(['all', 'completed', 'processing', 'failed'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`whitespace-nowrap px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === filter
                    ? 'bg-primary text-white'
                    : 'bg-surface text-text-secondary hover:bg-gray-100 dark:hover:bg-gray-800 border border-border'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)} ({statusCounts[filter]})
              </button>
            ))}
          </div>
        </div>
        
        {/* Contracts list */}
        {filteredContracts.length === 0 ? (
          <Card className="p-8 text-center">
            <FileText className="w-12 h-12 text-text-secondary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">No contracts found</h3>
            <p className="text-text-secondary">
              {searchQuery ? 'Try a different search term' : 'Try changing your filters'}
            </p>
          </Card>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block">
              <Card className="overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-border">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                        Filename
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                        Uploaded
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                        Status
                      </th>
                      {activeTab === 'samples' && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                          Type
                        </th>
                      )}
                      {activeTab === 'my-contracts' && (
                        <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                          Actions
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredContracts.map((contract) => (
                      <tr
                        key={contract.contract_id}
                        className="transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50"
                      >
                        <td className="px-6 py-4">
                          <button
                            onClick={() => handleRowClick(contract)}
                            disabled={contract.processing_status !== 'completed'}
                            className="flex items-center gap-3 text-left w-full disabled:cursor-not-allowed"
                          >
                            <FileText className="w-5 h-5 text-text-secondary flex-shrink-0" />
                            <span className="text-text-primary font-medium">{contract.filename}</span>
                          </button>
                        </td>
                        <td className="px-6 py-4 text-sm text-text-secondary">
                          {formatDate(contract.uploaded_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-2">
                            {getStatusBadge(contract.processing_status)}
                            {contract.processing_status === 'failed' && contract.error_message && (
                              <span className="text-xs text-red-600 dark:text-red-400">
                                {contract.failed_stage ? `Failed at ${contract.failed_stage}: ` : ''}{contract.error_message}
                              </span>
                            )}
                          </div>
                        </td>
                        {activeTab === 'samples' && (
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 font-medium">
                              Sample
                            </span>
                          </td>
                        )}
                        {activeTab === 'my-contracts' && (
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-end gap-2">
                              {contract.processing_status === 'failed' && (
                                <button
                                  onClick={() => handleRetry(contract.contract_id)}
                                  disabled={actionLoading === contract.contract_id}
                                  className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Retry processing"
                                >
                                  <RotateCcw className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => setDeleteConfirmId(contract.contract_id)}
                                disabled={actionLoading === contract.contract_id}
                                className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Delete contract"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
            
            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {filteredContracts.map((contract) => (
                <Card
                  key={contract.contract_id}
                  className="p-4 transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <button
                      onClick={() => handleRowClick(contract)}
                      disabled={contract.processing_status !== 'completed'}
                      className="flex items-center gap-2 flex-1 min-w-0 text-left disabled:cursor-not-allowed"
                    >
                      <FileText className="w-5 h-5 text-text-secondary flex-shrink-0" />
                      <span className="text-text-primary font-medium truncate">{contract.filename}</span>
                    </button>
                    {contract.is_sample && (
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 font-medium ml-2">
                        Sample
                      </span>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm text-text-secondary">
                      {formatDate(contract.uploaded_at)}
                    </div>
                    <div>
                      {getStatusBadge(contract.processing_status)}
                    </div>
                    {contract.processing_status === 'failed' && contract.error_message && (
                      <div className="text-xs text-red-600 dark:text-red-400 mt-1">
                        {contract.failed_stage ? `Failed at ${contract.failed_stage}: ` : ''}{contract.error_message}
                      </div>
                    )}
                    {!contract.is_sample && activeTab === 'my-contracts' && (
                      <div className="flex gap-2 pt-2">
                        {contract.processing_status === 'failed' && (
                          <Button
                            onClick={() => handleRetry(contract.contract_id)}
                            disabled={actionLoading === contract.contract_id}
                            variant="secondary"
                            className="flex-1 text-sm"
                          >
                            <RotateCcw className="w-4 h-4 mr-1" />
                            Retry
                          </Button>
                        )}
                        <Button
                          onClick={() => setDeleteConfirmId(contract.contract_id)}
                          disabled={actionLoading === contract.contract_id}
                          variant="secondary"
                          className="flex-1 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Delete
                        </Button>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </>
        )}
      </motion.div>
      
      {/* Delete confirmation modal */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface rounded-lg shadow-xl max-w-md w-full p-6"
          >
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Delete this contract?
            </h3>
            <p className="text-text-secondary mb-6">
              This cannot be undone. All analysis data will be permanently deleted.
            </p>
            {actionError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded text-sm">
                {actionError}
              </div>
            )}
            <div className="flex gap-3 justify-end">
              <Button
                onClick={() => {
                  setDeleteConfirmId(null);
                  setActionError(null);
                }}
                variant="secondary"
                disabled={actionLoading !== null}
              >
                Cancel
              </Button>
              <Button
                onClick={() => handleDelete(deleteConfirmId)}
                variant="primary"
                disabled={actionLoading !== null}
                className="bg-red-600 hover:bg-red-700"
              >
                {actionLoading === deleteConfirmId ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AppShell>
  );
}
