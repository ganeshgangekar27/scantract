import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExplanationPanel } from '../ExplanationPanel';
import type { RiskyClauseReport } from '../../types/report.types';

describe('ExplanationPanel', () => {
  const mockClause: RiskyClauseReport = {
    finding_id: 'uuid-123',
    clause_id: 1,
    clause_number: '4.2',
    clause_text: 'The tenant must pay rent within 3 days or face immediate eviction.',
    severity: 'high',
    reason: 'Extremely short notice period',
    explanation: 'This clause provides insufficient time for the tenant to remedy payment issues.',
    formatted_citation: 'Indian Rent Control Act, Section 12',
  };

  it('renders when clause provided', () => {
    render(<ExplanationPanel clause={mockClause} onClose={vi.fn()} />);
    
    expect(screen.getByText('Risk Details')).toBeInTheDocument();
    expect(screen.getByText('Clause 4.2')).toBeInTheDocument();
    expect(screen.getByText(/tenant must pay rent/)).toBeInTheDocument();
  });

  it('shows severity badge with correct color for high', () => {
    render(<ExplanationPanel clause={mockClause} onClose={vi.fn()} />);
    
    const badge = screen.getByText('HIGH');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('shows severity badge with correct color for medium', () => {
    const mediumClause = { ...mockClause, severity: 'medium' as const };
    render(<ExplanationPanel clause={mediumClause} onClose={vi.fn()} />);
    
    const badge = screen.getByText('MEDIUM');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('shows severity badge with correct color for low', () => {
    const lowClause = { ...mockClause, severity: 'low' as const };
    render(<ExplanationPanel clause={lowClause} onClose={vi.fn()} />);
    
    const badge = screen.getByText('LOW');
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('displays explanation and citation', () => {
    render(<ExplanationPanel clause={mockClause} onClose={vi.fn()} />);
    
    expect(screen.getByText('Why This is Risky')).toBeInTheDocument();
    expect(screen.getByText('Extremely short notice period')).toBeInTheDocument();
    
    expect(screen.getByText('Detailed Explanation')).toBeInTheDocument();
    expect(screen.getByText(/insufficient time for the tenant/)).toBeInTheDocument();
    
    expect(screen.getByText('Legal Reference')).toBeInTheDocument();
    expect(screen.getByText(/Indian Rent Control Act/)).toBeInTheDocument();
  });

  it('close button fires onClose handler', async () => {
    const mockOnClose = vi.fn();
    render(<ExplanationPanel clause={mockClause} onClose={mockOnClose} />);
    
    const closeButton = screen.getByLabelText('Close panel');
    await userEvent.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('does not render when clause is null', () => {
    const { container } = render(<ExplanationPanel clause={null} onClose={vi.fn()} />);
    
    expect(container.firstChild).toBeNull();
  });
});
