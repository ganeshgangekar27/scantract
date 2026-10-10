import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Palette, Shield, AlertTriangle } from 'lucide-react';
import { AppShell } from '../components/AppShell';
import { Card, Button, Modal, Input, ThemeToggle } from '../components/ui';
import { useAuth } from '../auth/AuthContext';
import { deleteMyData } from '../lib/api';
import { toast } from 'sonner';

export function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  
  const handleDeleteMyData = async () => {
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      
      await deleteMyData();
      
      // Clear token and logout
      localStorage.removeItem('scantract_token');
      logout();
      
      toast.success('All your data has been deleted');
      navigate('/login');
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete data');
    } finally {
      setDeleteLoading(false);
    }
  };
  
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };
  
  const isDeleteButtonEnabled = deleteConfirmText === 'DELETE';
  
  return (
    <AppShell title="Settings">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Account Card */}
        <Card>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <User className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Account</h2>
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-text-secondary mb-1">Name</div>
                  <div className="text-base text-text-primary">{user?.full_name}</div>
                </div>
                <div>
                  <div className="text-sm text-text-secondary mb-1">Email</div>
                  <div className="text-base text-text-primary">{user?.email}</div>
                </div>
                <div>
                  <div className="text-sm text-text-secondary mb-1">Member since</div>
                  <div className="text-base text-text-primary">
                    {user?.created_at ? formatDate(user.created_at) : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
        
        {/* Appearance Card */}
        <Card>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Palette className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Appearance</h2>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base text-text-primary mb-1">Theme</div>
                  <div className="text-sm text-text-secondary">
                    Choose between light and dark mode
                  </div>
                </div>
                <ThemeToggle />
              </div>
            </div>
          </div>
        </Card>
        
        {/* Privacy Card */}
        <Card>
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Privacy</h2>
              <div className="space-y-3 text-sm text-text-secondary">
                <p>
                  ScanTract stores your uploaded contracts, extracted clauses, and risk findings 
                  to provide analysis and reports.
                </p>
                <p>
                  Your data is private and only accessible to you. We use industry-standard 
                  encryption and security practices to protect your information.
                </p>
                <p>
                  You can delete all your data at any time using the option below. 
                  This action is permanent and cannot be undone.
                </p>
              </div>
            </div>
          </div>
        </Card>
        
        {/* Danger Zone Card */}
        <Card className="border-red-200 dark:border-red-900">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-red-100 dark:bg-red-900/20 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-500" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-red-600 dark:text-red-500 mb-4">
                Danger Zone
              </h2>
              <div className="space-y-4">
                <div>
                  <div className="text-base text-text-primary mb-2">Delete my data</div>
                  <div className="text-sm text-text-secondary mb-4">
                    Permanently delete all your contracts, analysis results, and account. 
                    This action cannot be undone.
                  </div>
                  <Button
                    variant="danger"
                    onClick={() => setDeleteModalOpen(true)}
                  >
                    Delete my data
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
      
      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setDeleteConfirmText('');
          setDeleteError(null);
        }}
        title="Delete all your data"
      >
        <div className="space-y-4">
          <p className="text-text-secondary">
            This will permanently delete all your contracts, analysis results, and account. 
            This action cannot be undone.
          </p>
          
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Type <span className="font-bold">DELETE</span> to confirm
            </label>
            <Input
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="Type DELETE to confirm"
              disabled={deleteLoading}
            />
          </div>
          
          {deleteError && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 rounded-lg">
              <p className="text-sm text-red-600 dark:text-red-500">{deleteError}</p>
            </div>
          )}
          
          <div className="flex gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => {
                setDeleteModalOpen(false);
                setDeleteConfirmText('');
                setDeleteError(null);
              }}
              disabled={deleteLoading}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteMyData}
              disabled={!isDeleteButtonEnabled || deleteLoading}
              className="flex-1"
            >
              {deleteLoading ? 'Deleting...' : 'Delete my data'}
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}
