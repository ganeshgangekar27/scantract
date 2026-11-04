import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { ForgotPasswordPage } from './ForgotPasswordPage';
import { AuthProvider } from '../../auth/AuthContext';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
    vi.mocked(localStorage.getItem).mockReturnValue(null);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  const renderForgotPasswordPage = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <ForgotPasswordPage />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('shows neutral success state after submission', async () => {
    const user = userEvent.setup();
    renderForgotPasswordPage();

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ message: 'Reset link sent' }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
      expect(screen.getByText(/if an account exists/i)).toBeInTheDocument();
    });
  });

  it('displays demo reset link card when provided', async () => {
    const user = userEvent.setup();
    renderForgotPasswordPage();

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        message: 'Reset link sent',
        demo_reset_link: 'http://localhost:5173/reset-password?token=demo-token-123',
      }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText(/demo mode: open reset link/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /open reset link/i })).toBeInTheDocument();
    });
  });

  it('does not show demo link when not in demo mode', async () => {
    const user = userEvent.setup();
    renderForgotPasswordPage();

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ message: 'Reset link sent' }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.queryByText(/demo mode/i)).not.toBeInTheDocument();
    });
  });

  it('shows unavailable message when VITE_RESET_DISABLED is true', () => {
    vi.stubEnv('VITE_RESET_DISABLED', 'true');
    renderForgotPasswordPage();

    expect(screen.getByText(/password reset unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/email password reset is not available on this site/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /back to login/i })).toBeInTheDocument();
  });

  it('does not call forgotPassword API when reset is disabled', () => {
    vi.stubEnv('VITE_RESET_DISABLED', 'true');
    const mockFetch = vi.mocked(globalThis.fetch);
    renderForgotPasswordPage();

    expect(mockFetch).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /send reset link/i })).not.toBeInTheDocument();
  });

  it('shows email input when VITE_RESET_DISABLED is not set', () => {
    vi.unstubAllEnvs();
    renderForgotPasswordPage();

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
    expect(screen.queryByText(/password reset unavailable/i)).not.toBeInTheDocument();
  });
});
