import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ReportView } from './ReportView';
import * as AuthContext from '../auth/AuthContext';
import type { Report } from '../lib/types';

// Mock API functions
vi.mock('../lib/api', () => ({
  getReport: vi.fn(),
  downloadReportPdf: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  },
}));

import * as api from '../lib/api';

// Spy on useAuth
vi.spyOn(AuthContext, 'useAuth');

// Fixture based on contract 46 structure
const mockReport: Report = {
  contract_id: 46,
  filename: 'sample-rental-agreement.pdf',
  upload_date: '2024-01-15T10:30:00Z',
  all_clauses: [],
  risky_clauses: [
    {
      finding_id: 'finding-1',
      clause_id: 101,
      clause_number: '3.1',
      clause_text: 'Tenant agrees to maintain insurance at their own expense.',
      severity: 'high',
      reason: 'Maintenance obligation is unusually broad',
      explanation: 'This clause places full maintenance responsibility on tenant which is uncommon',
      formatted_citation: 'Ref: Indian Contract Act, Section 123',
    },
    {
      finding_id: 'finding-2',
      clause_id: 102,
      clause_number: '4.2',
      clause_text: 'Landlord may terminate with 7 days notice.',
      severity: 'medium',
      reason: 'Short notice period',
      explanation: 'Notice period is below standard 30-day requirement',
      formatted_citation: 'Ref: Rent Control Act, 1948',
    },
    {
      finding_id: 'finding-3',
      clause_id: 101,
      clause_number: '3.1',
      clause_text: 'Tenant agrees to maintain insurance at their own expense.',
      severity: 'low',
      reason: 'Insurance clause lacks specific coverage amounts',
      explanation: 'The clause should specify minimum coverage requirements',
      formatted_citation: 'Ref: Insurance Act, 1938',
    },
  ],
  missing_clauses: [
    {
      finding_id: 'missing-1',
      expected_clause_type: 'Force Majeure',
      severity: 'medium',
      reason: 'Missing force majeure clause',
      explanation: 'Contract lacks provisions for extraordinary events',
      formatted_citation: 'Ref: Indian Contract Act, Section 56',
    },
  ],
  risk_summary: {
    total_clauses: 12,
    risky_clauses_count: 3,
    missing_clauses_count: 1,
    high_severity_count: 1,
    medium_severity_count: 2,
    low_severity_count: 1,
    overall_risk_level: 'medium',
  },
  legal_references: [],
};

describe('ReportView', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();

    // Mock useAuth to return authenticated user
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: { id: 1, email: 'test@example.com', full_name: 'Test User' },
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      forgotPassword: vi.fn(),
      resetPassword: vi.fn(),
    });
  });

  const renderReportView = (contractId = '46') => {
    return render(
      <MemoryRouter initialEntries={[`/contracts/${contractId}`]}>
        <Routes>
          <Route path="/contracts/:contractId" element={<ReportView />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders counts from fixture', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    // Wait for loading to complete
    expect(await screen.findByText('sample-rental-agreement.pdf')).toBeInTheDocument();

    // Check specific count sections
    const allText = screen.getByText(/All \(3\)/i);
    expect(allText).toBeInTheDocument();

    const highText = screen.getByText(/High \(1\)/i);
    expect(highText).toBeInTheDocument();

    const mediumText = screen.getByText(/Medium \(2\)/i);
    expect(mediumText).toBeInTheDocument();

    const lowText = screen.getByText(/Low \(1\)/i);
    expect(lowText).toBeInTheDocument();

    // Check header counts
    expect(screen.getByText('Missing')).toBeInTheDocument();
  });

  it('chip High shows only high findings', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    // Wait for loading
    await screen.findByText('sample-rental-agreement.pdf');

    // Click High filter
    const highButton = screen.getByRole('button', { name: /High \(1\)/i });
    await userEvent.click(highButton);

    // Should show only the high severity finding
    expect(await screen.findByText('Maintenance obligation is unusually broad')).toBeInTheDocument();
    
    // Should not show medium severity finding
    expect(screen.queryByText('Short notice period')).not.toBeInTheDocument();
    
    // Should not show low severity finding  
    expect(screen.queryByText('Insurance clause lacks specific coverage amounts')).not.toBeInTheDocument();
  });

  it('two findings with same clause_id but different finding_id both render', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Both findings for clause 101 should be visible (they have different reasons)
    expect(await screen.findByText('Maintenance obligation is unusually broad')).toBeInTheDocument();
    expect(screen.getByText('Insurance clause lacks specific coverage amounts')).toBeInTheDocument();
    
    // Both should have same clause number and text
    const clauseNumbers = screen.getAllByText('Clause 3.1');
    expect(clauseNumbers).toHaveLength(2);
  });

  it('409 shows not-finished message', async () => {
    const ApiError = (await import('../lib/api')).ApiError;
    vi.mocked(api.getReport).mockRejectedValueOnce(new ApiError(409, 'Analysis in progress'));

    renderReportView();

    expect(await screen.findByText('Analysis not finished yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
  });

  it('404 shows not-found message', async () => {
    const ApiError = (await import('../lib/api')).ApiError;
    vi.mocked(api.getReport).mockRejectedValueOnce(new ApiError(404, 'Not found'));

    renderReportView();

    expect(await screen.findByText('Contract not found')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
  });

  it('PDF button calls downloadReportPdf', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);
    vi.mocked(api.downloadReportPdf).mockResolvedValueOnce(new Blob(['pdf content'], { type: 'application/pdf' }));

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    const downloadButton = screen.getByRole('button', { name: /Download PDF/i });
    await userEvent.click(downloadButton);

    expect(api.downloadReportPdf).toHaveBeenCalledWith(46);
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });

  it('disclaimer text present', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    expect(
      await screen.findByText(
        /ScanTract is an educational tool, not legal advice\. The knowledge base is sample data and has not been verified by a lawyer\./i
      )
    ).toBeInTheDocument();
  });

  it('clicking finding shows why-flagged panel with reason', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Initially panel shows hint (appears twice - mobile and desktop)
    const hints = screen.getAllByText(/Select a finding to see why it was flagged/i);
    expect(hints.length).toBeGreaterThanOrEqual(1);

    // Click first finding
    const firstFinding = screen.getByText('Maintenance obligation is unusually broad');
    await userEvent.click(firstFinding);

    // Panel should show "Why Flagged" (appears twice - mobile and desktop)
    const panels = await screen.findAllByText('Why Flagged');
    expect(panels.length).toBeGreaterThanOrEqual(1);
    
    // Should show the reason in the panel
    const reasons = screen.getAllByText('Maintenance obligation is unusually broad');
    expect(reasons.length).toBeGreaterThan(1); // Once in card, once in panel
  });

  it('clicking another finding replaces panel content', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Click first finding
    const firstFinding = screen.getByText('Maintenance obligation is unusually broad');
    await userEvent.click(firstFinding);

    // "Why Flagged" appears in both mobile and desktop panels
    const panels = await screen.findAllByText('Why Flagged');
    expect(panels.length).toBeGreaterThanOrEqual(1);

    // Click second finding
    const secondFinding = screen.getByText('Short notice period');
    await userEvent.click(secondFinding);

    // Panel should now show second finding's content (appears in multiple places)
    const explanations = screen.getAllByText(/Notice period is below standard 30-day requirement/i);
    expect(explanations.length).toBeGreaterThan(0);
  });
});
