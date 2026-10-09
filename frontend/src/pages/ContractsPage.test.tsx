import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ContractsPage } from './ContractsPage';
import * as AuthContext from '../auth/AuthContext';
import * as api from '../lib/api';
import type { ContractListItem } from '../lib/types';

const mockUser = {
  id: 1,
  email: 'test@example.com',
  full_name: 'Test User',
};

const mockContracts: ContractListItem[] = [
  {
    contract_id: 1,
    filename: 'rental_agreement.pdf',
    uploaded_at: new Date('2026-10-09T10:00:00Z').toISOString(),
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 2,
    filename: 'freelance_contract.pdf',
    uploaded_at: new Date('2026-10-08T10:00:00Z').toISOString(),
    processing_status: 'processing',
    pipeline_stage: 'classification',
    failed_stage: null,
    error_message: null,
    is_sample: false,
  },
  {
    contract_id: 3,
    filename: 'employment_contract.pdf',
    uploaded_at: new Date('2026-10-07T10:00:00Z').toISOString(),
    processing_status: 'failed',
    pipeline_stage: null,
    failed_stage: 'extraction',
    error_message: 'File corrupted or unreadable',
    is_sample: false,
  },
  {
    contract_id: 100,
    filename: 'sample_rental.pdf',
    uploaded_at: new Date('2026-09-01T10:00:00Z').toISOString(),
    processing_status: 'completed',
    pipeline_stage: null,
    failed_stage: null,
    error_message: null,
    is_sample: true,
  },
];

describe('ContractsPage', () => {
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

  it('filters by search query', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    const rentalElements = await screen.findAllByText('rental_agreement.pdf');
    expect(rentalElements.length).toBeGreaterThanOrEqual(1); // Desktop + mobile
    expect(screen.getAllByText('freelance_contract.pdf').length).toBeGreaterThanOrEqual(1);
    
    // Search for 'rental'
    const searchBox = screen.getByPlaceholderText(/search contracts/i);
    await user.type(searchBox, 'rental');
    
    // Only rental_agreement.pdf should appear
    expect(screen.getAllByText('rental_agreement.pdf').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText('freelance_contract.pdf')).not.toBeInTheDocument();
    expect(screen.queryByText('employment_contract.pdf')).not.toBeInTheDocument();
  });

  it('filters by status chip', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    const rentalElements = await screen.findAllByText('rental_agreement.pdf');
    expect(rentalElements.length).toBeGreaterThanOrEqual(1);
    
    // Click 'Completed' filter
    await user.click(screen.getByRole('button', { name: /completed \(1\)/i }));
    
    // Only completed contracts should appear
    expect(screen.getAllByText('rental_agreement.pdf').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText('freelance_contract.pdf')).not.toBeInTheDocument();
    expect(screen.queryByText('employment_contract.pdf')).not.toBeInTheDocument();
  });

  it('shows failed row with error message', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    const employmentElements = await screen.findAllByText('employment_contract.pdf');
    expect(employmentElements.length).toBeGreaterThanOrEqual(1);
    
    const errorElements = screen.getAllByText(/File corrupted or unreadable/i);
    expect(errorElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows sample only under Samples tab', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    const rentalElements = await screen.findAllByText('rental_agreement.pdf');
    expect(rentalElements.length).toBeGreaterThanOrEqual(1);
    
    // Sample should not appear in My Contracts tab
    expect(screen.queryByText('sample_rental.pdf')).not.toBeInTheDocument();
    
    // Click Samples tab
    await user.click(screen.getByRole('button', { name: /samples \(1\)/i }));
    
    // Now sample should appear
    const sampleElements = await screen.findAllByText('sample_rental.pdf');
    expect(sampleElements.length).toBeGreaterThanOrEqual(1);
    
    // User contracts should not appear
    expect(screen.queryByText('rental_agreement.pdf')).not.toBeInTheDocument();
  });

  it('shows empty state when no user contracts', async () => {
    const onlySamples = mockContracts.filter(c => c.is_sample);
    vi.spyOn(api, 'listContracts').mockResolvedValue(onlySamples);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText('No contracts yet')).toBeInTheDocument();
    expect(screen.getByText(/Upload your first contract/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload contract/i })).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    vi.spyOn(api, 'listContracts').mockRejectedValue(new Error('API error'));
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    expect(await screen.findByText('Failed to load contracts')).toBeInTheDocument();
    expect(screen.getByText('API error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('retries loading when retry button clicked', async () => {
    const listContractsSpy = vi.spyOn(api, 'listContracts')
      .mockRejectedValueOnce(new Error('API error'))
      .mockResolvedValueOnce(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for error
    expect(await screen.findByText('Failed to load contracts')).toBeInTheDocument();
    
    // Click retry
    await user.click(screen.getByRole('button', { name: /retry/i }));
    
    // Should load successfully
    const rentalElements = await screen.findAllByText('rental_agreement.pdf');
    expect(rentalElements.length).toBeGreaterThanOrEqual(1);
    expect(listContractsSpy).toHaveBeenCalledTimes(2);
  });

  it('sorts contracts by date descending', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Get all contract rows (desktop table) - skip header row
    const table = screen.getByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    
    // Check order: newest first (rental_agreement, then freelance, then employment)
    expect(within(rows[0]).getAllByText('rental_agreement.pdf')[0]).toBeInTheDocument();
    expect(within(rows[1]).getAllByText('freelance_contract.pdf')[0]).toBeInTheDocument();
    expect(within(rows[2]).getAllByText('employment_contract.pdf')[0]).toBeInTheDocument();
  });

  it('shows correct status counts in filter chips', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Check filter chip counts
    expect(screen.getByRole('button', { name: /all \(3\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /completed \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /processing \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /failed \(1\)/i })).toBeInTheDocument();
  });

  it('disables click on non-completed contracts', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('freelance_contract.pdf');
    
    // Find the table (desktop view)
    const table = screen.getByRole('table');
    const processingRow = within(table).getAllByText('freelance_contract.pdf')[0].closest('tr');
    
    // Processing contract should not be clickable
    expect(processingRow).toHaveClass('cursor-not-allowed');
    expect(processingRow).toHaveClass('opacity-70');
  });
});
