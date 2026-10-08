import { useNavigate } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { EmptyState } from '../components/ui';
import { FileText } from 'lucide-react';

export function ContractsPage() {
  const navigate = useNavigate();
  
  return (
    <AppShell title="My Contracts">
      <EmptyState
        icon={FileText}
        title="No contracts yet"
        description="Upload your first contract to start analyzing for risks and missing clauses."
        action={{
          label: 'Upload Contract',
          onClick: () => navigate('/upload'),
        }}
      />
    </AppShell>
  );
}
