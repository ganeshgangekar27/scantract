import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ResetPasswordPage } from './ResetPasswordPage';
import { AuthProvider } from '../../auth/AuthContext';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
  });

  const renderWithToken = (token?: string) => {
    const url = token ? `/reset-password?token=${token}` : '/reset-password';
    return render(
      <MemoryRouter initialEntries={[url]}>
        <AuthProvider>
          <ResetPasswordPage />
        </AuthProvider>
      </MemoryRouter>
    );
  };

  it('shows error state when token is missing', async () => {
    renderWithToken();

    await waitFor(() => {
      expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /request a new link/i })).toBeInTheDocument();
    });
  });

  it('shows error state when link is expired', async () => {
    const user = userEvent.setup();
    renderWithToken('valid-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Password reset link has expired' }),
    });

    const passwordInputs = screen.getAllByLabelText(/password/i);
    await user.type(passwordInputs[0], 'newpassword123');
    await user.type(passwordInputs[1], 'newpassword123');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /request a new link/i })).toBeInTheDocument();
    });
  });

  it('shows error state when link is already used', async () => {
    const user = userEvent.setup();
    renderWithToken('used-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Password reset link already used' }),
    });

    const passwordInputs = screen.getAllByLabelText(/password/i);
    await user.type(passwordInputs[0], 'newpassword123');
    await user.type(passwordInputs[1], 'newpassword123');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
    });
  });

  it('shows error state when token is invalid', async () => {
    const user = userEvent.setup();
    renderWithToken('invalid-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Invalid password reset link' }),
    });

    const passwordInputs = screen.getAllByLabelText(/password/i);
    await user.type(passwordInputs[0], 'newpassword123');
    await user.type(passwordInputs[1], 'newpassword123');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
    });
  });

  it('navigates to login after successful password reset', async () => {
    const user = userEvent.setup();
    renderWithToken('valid-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Password reset successfully' }),
    });

    const passwordInputs = screen.getAllByLabelText(/password/i);
    await user.type(passwordInputs[0], 'newpassword123');
    await user.type(passwordInputs[1], 'newpassword123');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  it('validates password confirmation', async () => {
    const user = userEvent.setup();
    renderWithToken('valid-token');

    const passwordInputs = screen.getAllByLabelText(/password/i);
    await user.type(passwordInputs[0], 'password123');
    await user.type(passwordInputs[1], 'different456');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });
});
