import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RiskSummaryHeader } from '../RiskSummaryHeader';
import type { ContractReport } from '../../types/report.types';
import * as usePDFDownloadModule from '../../hooks/usePDFDownload';

// Mock usePDFDownload hook
vi.mock('../../hooks/usePDFDownload');

const mockReport: ContractReport = {
  contract_id: 1,
  filename: 'test_contract.pdf',
  upload_date: '2026-08-25T12:00:00Z',
  all_clauses: [],
  risky_clauses: [],
  missing_clauses: [],
  risk_summary: {
    total_clauses: 10,
    risky_clauses_count: 3,
    missing_clauses_count: 1,
    high_severity_count: 1,
    medium_severity_count: 1,
    low_severity_count: 1,
    overall_risk_level: 'medium',
  },
  legal_references: [],
};

describe('RiskSummaryHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders contract metadata correctly', () => {
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: vi.fn(),
      downloading: false,
      error: null,
    });

    render(<RiskSummaryHeader report={mockReport} contractId={1} />);
    
    expect(screen.getByText('test_contract.pdf')).toBeInTheDocument();
    expect(screen.getByText(/Uploaded on/)).toBeInTheDocument();
  });

  it('shows correct risk level badge color for medium', () => {
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: vi.fn(),
      downloading: false,
      error: null,
    });

    render(<RiskSummaryHeader report={mockReport} contractId={1} />);
    
    const badge = screen.getByText('MEDIUM');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('shows correct risk level badge color for high', () => {
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: vi.fn(),
      downloading: false,
      error: null,
    });

    const highRiskReport = {
      ...mockReport,
      risk_summary: { ...mockReport.risk_summary, overall_risk_level: 'high' as const },
    };

    render(<RiskSummaryHeader report={highRiskReport} contractId={1} />);
    
    const badge = screen.getByText('HIGH');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('displays severity counts correctly', () => {
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: vi.fn(),
      downloading: false,
      error: null,
    });

    render(<RiskSummaryHeader report={mockReport} contractId={1} />);
    
    expect(screen.getByText('10')).toBeInTheDocument(); // Total clauses
    expect(screen.getByText('High:')).toBeInTheDocument();
    expect(screen.getByText('Medium:')).toBeInTheDocument();
    expect(screen.getByText('Low:')).toBeInTheDocument();
  });

  it('PDF button shows loading state while downloading', () => {
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: vi.fn(),
      downloading: true,
      error: null,
    });

    render(<RiskSummaryHeader report={mockReport} contractId={1} />);
    
    expect(screen.getByText('Downloading...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('PDF button shows error alert when download fails with 500', async () => {
    const mockDownloadPDF = vi.fn().mockRejectedValue(new Error('PDF generation error'));
    
    vi.mocked(usePDFDownloadModule.usePDFDownload).mockReturnValue({
      downloadPDF: mockDownloadPDF,
      downloading: false,
      error: 'PDF generation is currently unavailable. This feature requires Docker deployment.',
    });

    render(<RiskSummaryHeader report={mockReport} contractId={1} />);
    
    const button = screen.getByText('Download PDF');
    await userEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText(/PDF generation is currently unavailable/)).toBeInTheDocument();
    });
  });
});
