import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ProtectedRoute, PublicOnlyRoute } from './ProtectedRoute';
import * as AuthContext from './AuthContext';

// Mock useAuth hook
vi.spyOn(AuthContext, 'useAuth');

describe('ProtectedRoute', () => {
  it('redirects to login when not authenticated', () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      forgotPassword: vi.fn(),
      resetPassword: vi.fn(),
    });
    
    const { container } = render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );
    
    expect(container.textContent).not.toContain('Protected Content');
  });
});

describe('PublicOnlyRoute', () => {
  it('redirects to dashboard when authenticated', () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, email: 'test@example.com', full_name: 'Test User', created_at: '', is_active: true },
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      forgotPassword: vi.fn(),
      resetPassword: vi.fn(),
    });
    
    const { container } = render(
      <BrowserRouter>
        <PublicOnlyRoute>
          <div>Public Content</div>
        </PublicOnlyRoute>
      </BrowserRouter>
    );
    
    expect(container.textContent).not.toContain('Public Content');
  });
});
