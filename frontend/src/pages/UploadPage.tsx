import { AppShell } from '../components/AppShell';
import { ContractUpload } from '../components/ContractUpload';

export function UploadPage() {
  return (
    <AppShell title="Upload Contract">
      <ContractUpload />
    </AppShell>
  );
}
