import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { SettingsPage } from './SettingsPage';
import * as api from '../lib/api';

// Mock AuthContext
const mockLogout = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
      created_at: '2024-01-15T10:30:00Z',
      is_active: true,
    },
    logout: mockLogout,
  }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../lib/api');

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  it('renders all four cards', () => {
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    expect(screen.getByText('Account')).toBeInTheDocument();
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByText('Privacy')).toBeInTheDocument();
    expect(screen.getByText('Danger Zone')).toBeInTheDocument();
  });
  
  it('displays user information in Account card', () => {
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
    expect(screen.getByText('January 15, 2024')).toBeInTheDocument();
  });
  
  it('delete button is disabled until DELETE is typed', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete my data/i });
    await user.click(deleteButton);
    
    // Modal should be open - look for modal title
    await waitFor(() => {
      expect(screen.getByText('Delete all your data')).toBeInTheDocument();
    });
    
    // Confirm button should be disabled
    const confirmButton = screen.getAllByRole('button', { name: /delete my data/i })[1];
    expect(confirmButton).toBeDisabled();
    
    // Type wrong text
    const input = screen.getByPlaceholderText(/type delete to confirm/i);
    await user.type(input, 'delete');
    expect(confirmButton).toBeDisabled();
    
    // Clear and type correct text
    await user.clear(input);
    await user.type(input, 'DELETE');
    expect(confirmButton).not.toBeDisabled();
  });
  
  it('cancel button closes modal without calling API', async () => {
    const user = userEvent.setup();
    
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete my data/i });
    await user.click(deleteButton);
    
    // Wait for modal - check for title
    await waitFor(() => {
      expect(screen.getByText('Delete all your data')).toBeInTheDocument();
    });
    
    // Click cancel
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);
    
    // Modal should close
    await waitFor(() => {
      expect(screen.queryByText('Delete all your data')).not.toBeInTheDocument();
    });
    
    // API should not be called
    expect(api.deleteMyData).not.toHaveBeenCalled();
  });
  
  it('successful delete clears token, logs out, and navigates to login', async () => {
    const user = userEvent.setup();
    
    vi.mocked(api.deleteMyData).mockResolvedValue({ deleted_contracts: 5 });
    
    // Set token
    localStorage.setItem('scantract_token', 'test-token-123');
    
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete my data/i });
    await user.click(deleteButton);
    
    // Type DELETE
    const input = await screen.findByPlaceholderText(/type delete to confirm/i);
    await user.type(input, 'DELETE');
    
    // Click confirm
    const confirmButton = screen.getAllByRole('button', { name: /delete my data/i })[1];
    await user.click(confirmButton);
    
    // Wait for API call
    await waitFor(() => {
      expect(api.deleteMyData).toHaveBeenCalledTimes(1);
    });
    
    // Token should be cleared
    expect(localStorage.getItem('scantract_token')).toBeUndefined();
    
    // Logout should be called
    expect(mockLogout).toHaveBeenCalledTimes(1);
    
    // Should navigate to login
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });
  
  it('shows API error when delete fails', async () => {
    const user = userEvent.setup();
    
    vi.mocked(api.deleteMyData).mockRejectedValue(new Error('Server error'));
    
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );
    
    // Open modal
    const deleteButton = screen.getByRole('button', { name: /delete my data/i });
    await user.click(deleteButton);
    
    // Type DELETE
    const input = await screen.findByPlaceholderText(/type delete to confirm/i);
    await user.type(input, 'DELETE');
    
    // Click confirm
    const confirmButton = screen.getAllByRole('button', { name: /delete my data/i })[1];
    await user.click(confirmButton);
    
    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
    
    // Should not navigate
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
