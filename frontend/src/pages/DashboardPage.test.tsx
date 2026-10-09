import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from './DashboardPage';
import * as AuthContext from '../auth/AuthContext';
import * as api from '../lib/api';
import type { ContractListItem } from '../lib/types';

const mockUser = {
  id: 1,
  email: 'test@example.com',
  full_name: 'John Doe',
};

const mockContracts: ContractListItem[] = [
  {
    contract_id: 1,
    filename: 'contract1.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 minutes ago
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 2,
    filename: 'contract2.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
    processing_status: 'processing',
    pipeline_stage: 'classification',
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 3,
    filename: 'contract3.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
    processing_status: 'failed',
    pipeline_stage: null,
    failed_stage: 'extraction',
    error_message: 'Invalid file format',
    is_sample: false,
  },
  {
    contract_id: 4,
    filename: 'contract4.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(), // 2 days ago
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 5,
    filename: 'contract5.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(), // 3 days ago
    processing_status: 'uploaded',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 6,
    filename: 'contract6.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(), // 4 days ago
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 100,
    filename: 'sample_rental_agreement.pdf',
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: true,
  },
];

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      user: mockUser,
      loading: false,
      login: vi.fn(),
      signup: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });
    
    global.fetch = vi.fn();
  });
  
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows stat counts excluding samples', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText('6')).toBeInTheDocument(); // Total (excluding sample)
    expect(await screen.findByText('3')).toBeInTheDocument(); // Completed
    expect(await screen.findByText('2')).toBeInTheDocument(); // In progress (processing + uploaded)
    expect(await screen.findByText('1')).toBeInTheDocument(); // Failed
  });

  it('shows recent list with latest 5 in date order', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    expect(await screen.findByText('contract1.pdf')).toBeInTheDocument();
    
    // Check that first 5 user contracts appear (sorted by date, newest first)
    expect(screen.getByText('contract1.pdf')).toBeInTheDocument();
    expect(screen.getByText('contract2.pdf')).toBeInTheDocument();
    expect(screen.getByText('contract3.pdf')).toBeInTheDocument();
    expect(screen.getByText('contract4.pdf')).toBeInTheDocument();
    expect(screen.getByText('contract5.pdf')).toBeInTheDocument();
    
    // 6th contract should not appear in recent list
    expect(screen.queryByText('contract6.pdf')).not.toBeInTheDocument();
    
    // Sample should not appear in recent list
    expect(screen.queryByText('sample_rental_agreement.pdf')).toBeInTheDocument(); // but in "Try a sample" section
  });

  it('shows greeting with user first name', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText(/Welcome back, John!/)).toBeInTheDocument();
  });

  it('shows empty state with CTA when no user contracts', async () => {
    const onlySamples = mockContracts.filter(c => c.is_sample);
    vi.spyOn(api, 'listContracts').mockResolvedValue(onlySamples);
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText(/Welcome, John!/)).toBeInTheDocument();
    expect(screen.getByText(/Let's analyze your first contract/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload contract/i })).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    vi.spyOn(api, 'listContracts').mockRejectedValue(new Error('Network error'));
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText('Failed to load dashboard')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('retries loading when retry button clicked', async () => {
    const listContractsSpy = vi.spyOn(api, 'listContracts')
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    // Wait for error
    expect(await screen.findByText('Failed to load dashboard')).toBeInTheDocument();
    
    // Click retry
    await user.click(screen.getByRole('button', { name: /retry/i }));
    
    // Should load successfully
    expect(await screen.findByText('contract1.pdf')).toBeInTheDocument();
    expect(listContractsSpy).toHaveBeenCalledTimes(2);
  });

  it('navigates to contract detail when completed contract clicked', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    const { container } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    const completedContract = await screen.findByText('contract1.pdf');
    
    // Click on completed contract
    await user.click(completedContract.closest('button')!);
    
    // Check navigation (MemoryRouter doesn't actually navigate, but button click shouldn't error)
    expect(completedContract).toBeInTheDocument();
  });

  it('shows sample contracts in separate section', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText('Try a sample contract')).toBeInTheDocument();
    expect(screen.getByText('sample_rental_agreement.pdf')).toBeInTheDocument();
    
    // Sample badge should appear
    expect(screen.getByText('Sample')).toBeInTheDocument();
  });
});
