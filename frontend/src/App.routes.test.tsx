import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { ContractsPage } from './pages/ContractsPage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import * as AuthContext from './auth/AuthContext';

// Mock useAuth with a logged-in user
const mockUser = {
  id: 1,
  email: 'test@example.com',
  full_name: 'Test User',
};

describe('App routing', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: mockUser,
      loading: false,
      login: vi.fn(),
      signup: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });
  });

  it('renders Dashboard page at /dashboard', async () => {
    // Mock listContracts to return empty array for dashboard
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true, data: [] }),
    });
    
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    
    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(await screen.findByText(/let's analyze your first contract/i)).toBeInTheDocument();
    expect(screen.queryByText(/drag and drop your contract here/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/account settings and preferences/i)).not.toBeInTheDocument();
  });

  it('renders Upload page at /upload', async () => {
    render(
      <MemoryRouter initialEntries={['/upload']}>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    
    expect(await screen.findByText(/drag and drop your contract here/i)).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: /upload/i })[0]).toBeInTheDocument();
    expect(screen.queryByText(/welcome to scantract/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no contracts yet/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/account settings and preferences/i)).not.toBeInTheDocument();
  });

  it('renders Contracts page at /contracts', async () => {
    // Mock listContracts to return empty array
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true, data: [] }),
    });
    
    render(
      <MemoryRouter initialEntries={['/contracts']}>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    
    expect(await screen.findByRole('heading', { name: /my contracts/i })).toBeInTheDocument();
    expect(await screen.findByText(/upload your first contract/i)).toBeInTheDocument();
    expect(screen.queryByText(/let's analyze your first contract/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/drag and drop your contract here/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/account settings and preferences/i)).not.toBeInTheDocument();
  });

  it('renders Settings page at /settings', async () => {
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    
    expect(await screen.findByText(/danger zone/i)).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: /settings/i })[0]).toBeInTheDocument();
    expect(screen.queryByText(/welcome to scantract/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/drag and drop your contract here/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no contracts yet/i)).not.toBeInTheDocument();
  });

  it('renders NotFoundPage for unknown routes', async () => {
    render(
      <MemoryRouter initialEntries={['/unknown-path']}>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    
    expect(await screen.findByText(/page not found/i)).toBeInTheDocument();
  });
});
