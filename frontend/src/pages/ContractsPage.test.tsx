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
    const rows = within(table).getAllByRole('row');
    const processingRow = rows.find(row => within(row).queryByText('freelance_contract.pdf'));
    
    // Processing contract button should be disabled
    const buttons = within(processingRow!).getAllByRole('button');
    const fileButton = buttons.find(btn => btn.textContent?.includes('freelance_contract.pdf'));
    expect(fileButton).toBeDisabled();
  });
  
  it('shows Delete button for non-sample contracts', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Delete buttons should be present for user contracts (desktop + mobile = 2 per contract * 3 contracts = 6)
    const deleteButtons = screen.getAllByTitle('Delete contract');
    expect(deleteButtons.length).toBeGreaterThanOrEqual(3); // At least one per user contract
  });
  
  it('does not show Delete button on sample contracts', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Switch to Samples tab
    await user.click(screen.getByRole('button', { name: /samples \(1\)/i }));
    
    // Wait for sample to appear
    await screen.findAllByText('sample_rental.pdf');
    
    // No Delete buttons should be present
    expect(screen.queryByTitle('Delete contract')).not.toBeInTheDocument();
  });
  
  it('shows Retry button only on failed contracts', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('employment_contract.pdf');
    
    // Retry buttons should be present for failed contract (desktop + mobile = 2)
    const retryButtons = screen.getAllByTitle('Retry processing');
    expect(retryButtons.length).toBe(1); // Desktop only, mobile shows text button
    
    // Mobile has text buttons
    const mobileRetryButtons = screen.getAllByRole('button', { name: /retry/i });
    expect(mobileRetryButtons.length).toBeGreaterThanOrEqual(1);
  });
  
  it('clicking Delete opens confirmation modal', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Click first Delete button (desktop view)
    const deleteButtons = screen.getAllByTitle('Delete contract');
    await user.click(deleteButtons[0]);
    
    // Modal should appear
    expect(screen.getByText('Delete this contract?')).toBeInTheDocument();
    expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument();
  });
  
  it('cancel button closes modal without calling API', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    const deleteContractSpy = vi.spyOn(api, 'deleteContract');
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Click Delete button
    const deleteButtons = screen.getAllByTitle('Delete contract');
    await user.click(deleteButtons[0]);
    
    // Wait for modal
    expect(await screen.findByText('Delete this contract?')).toBeInTheDocument();
    
    // Click Cancel
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    
    // Modal should close
    expect(screen.queryByText('Delete this contract?')).not.toBeInTheDocument();
    
    // API should not be called
    expect(deleteContractSpy).not.toHaveBeenCalled();
  });
  
  it('successful delete calls API and reloads list', async () => {
    const listContractsSpy = vi.spyOn(api, 'listContracts')
      .mockResolvedValueOnce(mockContracts)
      .mockResolvedValueOnce(mockContracts.filter(c => c.contract_id !== 1));
    
    const deleteContractSpy = vi.spyOn(api, 'deleteContract').mockResolvedValue(undefined);
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Click Delete button (desktop view - first title="Delete contract" button)
    const deleteButtons = screen.getAllByTitle('Delete contract');
    await user.click(deleteButtons[0]);
    
    // Wait for modal and confirm - use getAllByRole and pick the last one (confirm button in modal)
    expect(await screen.findByText('Delete this contract?')).toBeInTheDocument();
    const allDeleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const confirmButton = allDeleteButtons[allDeleteButtons.length - 1]; // Last one is the confirm button
    await user.click(confirmButton);
    
    // Should call API
    expect(deleteContractSpy).toHaveBeenCalledWith(1);
    
    // Should reload list
    expect(listContractsSpy).toHaveBeenCalledTimes(2);
  });
  
  it('shows API error when delete fails', async () => {
    vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    vi.spyOn(api, 'deleteContract').mockRejectedValue(new Error('Permission denied'));
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('rental_agreement.pdf');
    
    // Click Delete button (desktop view)
    const deleteButtons = screen.getAllByTitle('Delete contract');
    await user.click(deleteButtons[0]);
    
    // Wait for modal and confirm - use getAllByRole and pick the last one
    expect(await screen.findByText('Delete this contract?')).toBeInTheDocument();
    const allDeleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const confirmButton = allDeleteButtons[allDeleteButtons.length - 1];
    await user.click(confirmButton);
    
    // Error should appear in modal
    expect(await screen.findByText('Permission denied')).toBeInTheDocument();
  });
  
  it('clicking Retry calls API and reloads list', async () => {
    const listContractsSpy = vi.spyOn(api, 'listContracts').mockResolvedValue(mockContracts);
    const retryContractSpy = vi.spyOn(api, 'retryContract').mockResolvedValue({ contract_id: 3 });
    
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <ContractsPage />
      </MemoryRouter>
    );
    
    // Wait for contracts to load
    await screen.findAllByText('employment_contract.pdf');
    
    // Click Retry button (desktop view)
    const retryButton = screen.getByTitle('Retry processing');
    await user.click(retryButton);
    
    // Should call API
    expect(retryContractSpy).toHaveBeenCalledWith(3);
    
    // Should reload list
    expect(listContractsSpy).toHaveBeenCalledTimes(2);
  });
});

