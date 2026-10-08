import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
import { AuthProvider } from '../../auth/AuthContext';

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    Link: actual.Link,
    BrowserRouter: actual.BrowserRouter,
  };
});

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
    // Clear mocks, not redefine
    vi.mocked(localStorage.getItem).mockReturnValue(null);
    vi.mocked(localStorage.setItem).mockClear();
    vi.mocked(sessionStorage.getItem).mockReturnValue(null);
    vi.mocked(sessionStorage.removeItem).mockClear();
  });

  const renderLoginPage = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('displays email-specific error under email field', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'No account found with this email' }),
    });

    await user.type(screen.getByLabelText('Email'), 'notfound@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/no account found/i)).toBeInTheDocument();
    });
  });

  it('displays password-specific error under password field', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Incorrect password' }),
    });

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/incorrect password/i)).toBeInTheDocument();
    });
  });

  it('stores token and navigates to dashboard after successful login', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    (globalThis.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          access_token: 'mock-token',
          token_type: 'bearer',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 1,
          email: 'test@example.com',
          full_name: 'Test User',
          created_at: '2024-01-01T00:00:00Z',
          is_active: true,
        }),
      });

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(localStorage.setItem).toHaveBeenCalledWith('scantract_token', 'mock-token');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('returns to originally wanted path after login', async () => {
    const user = userEvent.setup();
    vi.mocked(sessionStorage.getItem).mockReturnValue('/contracts/123');
    renderLoginPage();

    (globalThis.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          access_token: 'mock-token',
          token_type: 'bearer',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 1,
          email: 'test@example.com',
          full_name: 'Test User',
          created_at: '2024-01-01T00:00:00Z',
          is_active: true,
        }),
      });

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/contracts/123');
      expect(sessionStorage.removeItem).toHaveBeenCalledWith('redirect_after_login');
    });
  });

  it('shows forgot password link', () => {
    renderLoginPage();
    expect(screen.getByText(/forgot password\?/i)).toBeInTheDocument();
  });
});
