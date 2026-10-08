import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
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

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
    Object.defineProperty(globalThis, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      writable: true,
    });
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      writable: true,
    });
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
      json: async () => ({ detail: 'No account found with this email' }),
    });

    await user.type(screen.getByLabelText(/email/i), 'notfound@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
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
      json: async () => ({ detail: 'Incorrect password' }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/incorrect password/i)).toBeInTheDocument();
    });
  });

  it('stores token and navigates to dashboard after successful login', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const mockSetItem = vi.fn();
    (globalThis.localStorage as any).setItem = mockSetItem;

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'mock-token',
        token_type: 'bearer',
      }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(mockSetItem).toHaveBeenCalledWith('scantract_token', 'mock-token');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('returns to originally wanted path after login', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const mockGetItem = vi.fn((key) => key === 'redirect_after_login' ? '/contracts/123' : null);
    const mockRemoveItem = vi.fn();
    (globalThis.sessionStorage as any).getItem = mockGetItem;
    (globalThis.sessionStorage as any).removeItem = mockRemoveItem;

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'mock-token',
        token_type: 'bearer',
      }),
    });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/contracts/123');
      expect(mockRemoveItem).toHaveBeenCalledWith('redirect_after_login');
    });
  });

  it('shows forgot password link', () => {
    renderLoginPage();
    expect(screen.getByText(/forgot password\?/i)).toBeInTheDocument();
  });
});
