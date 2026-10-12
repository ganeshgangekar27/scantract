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

    // Check specific count sections (chips show risky-only counts after chip-count fix)
    const allText = screen.getByText(/All \(3\)/i);
    expect(allText).toBeInTheDocument();

    const highText = screen.getByText(/High \(1\)/i);
    expect(highText).toBeInTheDocument();

    const mediumText = screen.getByText(/Medium \(1\)/i);  // Only 1 risky medium (missing not counted in chip)
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

    // Should show 1 card
    const cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(1);
    
    // Click the high severity finding card to show reason in panel
    await userEvent.click(cards[0]);

    // Should show only the high severity finding (reason appears in panel after click - may appear in multiple panels)
    const reasons = await screen.findAllByText('Maintenance obligation is unusually broad');
    expect(reasons.length).toBeGreaterThanOrEqual(1);
    
    // Should not show medium severity finding
    expect(screen.queryByText('Short notice period')).not.toBeInTheDocument();
    
    // Should not show low severity finding  
    expect(screen.queryByText('Insurance clause lacks specific coverage amounts')).not.toBeInTheDocument();
  });

  it('two findings with same clause_id but different finding_id both render', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // All cards should render
    const cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(3);
    
    // Both findings have same clause number
    const clauseNumbers = screen.getAllByText('Clause 3.1');
    expect(clauseNumbers).toHaveLength(2);
    
    // Click first card with Clause 3.1 to see its reason in panel
    await userEvent.click(cards[0]);  // finding-1 (high)
    const reasons1 = await screen.findAllByText('Maintenance obligation is unusually broad');
    expect(reasons1.length).toBeGreaterThanOrEqual(1);
    
    // Click third card with Clause 3.1 to see its reason in panel
    await userEvent.click(cards[2]);  // finding-3 (low)
    const reasons2 = screen.getAllByText('Insurance clause lacks specific coverage amounts');
    expect(reasons2.length).toBeGreaterThanOrEqual(1);
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

    // Click first finding card (by clause number since cards are collapsed)
    const cards = screen.getAllByTestId('finding-card');
    await userEvent.click(cards[0]);

    // Panel should show "Why Flagged" (appears twice - mobile and desktop)
    const panels = await screen.findAllByText('Why Flagged');
    expect(panels.length).toBeGreaterThanOrEqual(1);
    
    // Should show the reason in the panel
    const reasons = screen.getAllByText('Maintenance obligation is unusually broad');
    expect(reasons).toHaveLength(2); // In both mobile and desktop panels
  });

  it('clicking another finding replaces panel content', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Click first finding card
    const cards = screen.getAllByTestId('finding-card');
    await userEvent.click(cards[0]);

    // "Why Flagged" appears in both mobile and desktop panels
    const panels = await screen.findAllByText('Why Flagged');
    expect(panels.length).toBeGreaterThanOrEqual(1);
    
    // First finding's reason should be visible in panel(s)
    const reasons1 = screen.getAllByText('Maintenance obligation is unusually broad');
    expect(reasons1.length).toBeGreaterThanOrEqual(1);

    // Click second finding card
    await userEvent.click(cards[1]);

    // Panel should now show second finding's reason
    const reasons2 = screen.getAllByText('Short notice period');
    expect(reasons2.length).toBeGreaterThanOrEqual(1);
    
    // First finding's reason should NOT be in the document anymore
    expect(screen.queryByText('Maintenance obligation is unusually broad')).not.toBeInTheDocument();
  });

  it('top risks section renders at most 5 rows', async () => {
    // Create mock report with more than 5 findings
    const manyFindings: Report = {
      ...mockReport,
      risky_clauses: Array.from({ length: 8 }, (_, i) => ({
        finding_id: `finding-${i}`,
        clause_id: 100 + i,
        clause_number: `${i + 1}.1`,
        clause_text: `Clause text ${i}`,
        severity: i < 3 ? 'high' : i < 6 ? 'medium' : 'low',
        reason: `Reason ${i}`,
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      })) as any,
      missing_clauses: [],
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(manyFindings);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Top risks section should be present
    const topRisksSection = screen.getByTestId('top-risks');
    expect(topRisksSection).toBeInTheDocument();

    // Should show exactly 5 rows
    const riskRows = screen.getAllByTestId('top-risk-row');
    expect(riskRows).toHaveLength(5);
  });

  it('top risks section shows risks in severity order', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Top risks section should be present
    const topRisksSection = screen.getByTestId('top-risks');
    expect(topRisksSection).toBeInTheDocument();

    // Get all risk rows
    const riskRows = screen.getAllByTestId('top-risk-row');

    // Should have 4 total risks (3 risky + 1 missing)
    expect(riskRows).toHaveLength(4);

    // Check badges to ensure high > medium > low order
    const badges = riskRows.map(row => row.querySelector('span')?.textContent);
    
    // First should be high
    expect(badges[0]).toBe('HIGH');
    
    // Next two should be medium (one risky, one missing)
    expect(badges[1]).toBe('MEDIUM');
    expect(badges[2]).toBe('MEDIUM');
    
    // Last should be low
    expect(badges[3]).toBe('LOW');
  });

  it('top risks section hidden when no findings', async () => {
    const emptyReport: Report = {
      ...mockReport,
      risky_clauses: [],
      missing_clauses: [],
      risk_summary: {
        total_clauses: 10,
        risky_clauses_count: 0,
        missing_clauses_count: 0,
        high_severity_count: 0,
        medium_severity_count: 0,
        low_severity_count: 0,
        overall_risk_level: 'none',
      },
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(emptyReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Top risks section should not be present
    expect(screen.queryByTestId('top-risks')).not.toBeInTheDocument();
  });

  it('finding cards are collapsed by default', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Cards should exist
    const cards = screen.getAllByTestId('finding-card');
    expect(cards.length).toBeGreaterThan(0);

    // finding-details should not be present (cards collapsed)
    expect(screen.queryByTestId('finding-details')).not.toBeInTheDocument();
  });

  it('clicking card expands to show details, clicking again collapses', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    const cards = screen.getAllByTestId('finding-card');
    
    // Initially collapsed
    expect(screen.queryByTestId('finding-details')).not.toBeInTheDocument();

    // Click to expand
    await userEvent.click(cards[0]);

    // Should now show finding-details with clause_text, explanation, citation
    const details = screen.getByTestId('finding-details');
    expect(details).toBeInTheDocument();
    expect(details).toHaveTextContent('Tenant agrees to maintain insurance');
    expect(details).toHaveTextContent('This clause places full maintenance responsibility');
    expect(details).toHaveTextContent('Ref: Indian Contract Act, Section 123');

    // Click again to collapse
    await userEvent.click(cards[0]);

    // Should be collapsed again
    expect(screen.queryByTestId('finding-details')).not.toBeInTheDocument();
  });

  it('shows 5 finding cards and "Show all 7" button with 7 risky findings', async () => {
    const sevenFindings: Report = {
      ...mockReport,
      risky_clauses: Array.from({ length: 7 }, (_, i) => ({
        finding_id: `finding-${i}`,
        clause_id: 100 + i,
        clause_number: `${i + 1}.1`,
        clause_text: `Clause text ${i}`,
        severity: 'high',
        reason: `Reason ${i}`,
        explanation: `Explanation ${i}`,
        formatted_citation: `Citation ${i}`,
      })) as any,
      missing_clauses: [],
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(sevenFindings);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Should show exactly 5 cards initially
    let cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(5);

    // Should show "Show all 7" button
    const showAllButton = screen.getByRole('button', { name: /Show all 7/i });
    expect(showAllButton).toBeInTheDocument();

    // Click the button
    await userEvent.click(showAllButton);

    // Should now show all 7 cards
    cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(7);

    // Button should be gone
    expect(screen.queryByRole('button', { name: /Show all 7/i })).not.toBeInTheDocument();
  });

  it('no "Show all" button when 5 or fewer findings', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);  // Has 3 risky findings

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Should show 3 cards (not limited to 5)
    const cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(3);

    // Should not show "Show all" button
    expect(screen.queryByRole('button', { name: /Show all/i })).not.toBeInTheDocument();
  });

  it('high chip with 6 high findings shows "Show all 6" button', async () => {
    const sixHighFindings: Report = {
      ...mockReport,
      risky_clauses: [
        ...Array.from({ length: 6 }, (_, i) => ({
          finding_id: `high-${i}`,
          clause_id: 100 + i,
          clause_number: `${i + 1}.1`,
          clause_text: `High clause ${i}`,
          severity: 'high' as const,
          reason: `High reason ${i}`,
          explanation: `Explanation ${i}`,
          formatted_citation: `Citation ${i}`,
        })),
        {
          finding_id: 'medium-1',
          clause_id: 200,
          clause_number: '10.1',
          clause_text: 'Medium clause',
          severity: 'medium' as const,
          reason: 'Medium reason',
          explanation: 'Medium explanation',
          formatted_citation: 'Citation',
        },
      ] as any,
      missing_clauses: [],
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(sixHighFindings);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Click High filter
    const highButton = screen.getByRole('button', { name: /High \(6\)/i });
    await userEvent.click(highButton);

    // Should show 5 cards initially
    let cards = screen.getAllByTestId('finding-card');
    expect(cards).toHaveLength(5);

    // Should show "Show all 6" button (filtered count)
    const showAllButton = screen.getByRole('button', { name: /Show all 6/i });
    expect(showAllButton).toBeInTheDocument();
  });

  it('chip count excludes missing clauses (high severity)', async () => {
    const mixedReport: Report = {
      ...mockReport,
      risky_clauses: [
        {
          finding_id: 'risky-high-1',
          clause_id: 101,
          clause_number: '1.1',
          clause_text: 'Risky high clause',
          severity: 'high',
          reason: 'Risky issue',
          explanation: 'Explanation',
          formatted_citation: 'Citation',
        },
      ],
      missing_clauses: [
        {
          finding_id: 'missing-high-1',
          expected_clause_type: 'Missing High Clause',
          severity: 'high',
          reason: 'Missing issue',
          explanation: 'Missing explanation',
          formatted_citation: 'Missing citation',
        },
      ],
      risk_summary: {
        total_clauses: 12,
        risky_clauses_count: 1,
        missing_clauses_count: 1,
        high_severity_count: 2,  // Combined: 1 risky + 1 missing
        medium_severity_count: 0,
        low_severity_count: 0,
        overall_risk_level: 'high',
      },
      legal_references: [],
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(mixedReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // High chip should show (1) for risky only, not (2) for combined
    const highButton = screen.getByRole('button', { name: /High \(1\)/i });
    expect(highButton).toBeInTheDocument();

    // Summary header should still show combined count (2) in the header "High" section
    // (The summary card uses combined counts, chips use risky-only counts)
  });

  it('severity bar is present for fixture report', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Severity bar should be present
    const bar = screen.getByTestId('severity-bar');
    expect(bar).toBeInTheDocument();
  });

  it('severity bar is absent for empty report', async () => {
    const emptyReport: Report = {
      ...mockReport,
      risky_clauses: [],
      missing_clauses: [],
      risk_summary: {
        ...mockReport.risk_summary,
        risky_clauses_count: 0,
        missing_clauses_count: 0,
        high_severity_count: 0,
        medium_severity_count: 0,
        low_severity_count: 0,
        overall_risk_level: 'low',
      },
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(emptyReport);

    renderReportView();

    await screen.findByText('sample-rental-agreement.pdf');

    // Severity bar should NOT be present when all counts are 0
    expect(screen.queryByTestId('severity-bar')).not.toBeInTheDocument();
  });
});


