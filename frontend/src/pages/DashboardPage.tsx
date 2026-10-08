import { useNavigate } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { EmptyState } from '../components/ui';
import { LayoutDashboard } from 'lucide-react';

export function DashboardPage() {
  const navigate = useNavigate();
  
  return (
    <AppShell title="Dashboard">
      <EmptyState
        icon={LayoutDashboard}
        title="Welcome to ScanTract"
        description="Your contract analysis dashboard. Upload a contract to get started."
        action={{
          label: 'Upload Contract',
          onClick: () => navigate('/upload'),
        }}
      />
    </AppShell>
  );
}
