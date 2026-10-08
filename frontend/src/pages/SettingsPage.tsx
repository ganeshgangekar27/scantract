import { AppShell } from '../components/AppShell';
import { EmptyState } from '../components/ui';
import { Settings } from 'lucide-react';

export function SettingsPage() {
  return (
    <AppShell title="Settings">
      <EmptyState
        icon={Settings}
        title="Settings"
        description="Account settings and preferences will be available here soon."
      />
    </AppShell>
  );
}
