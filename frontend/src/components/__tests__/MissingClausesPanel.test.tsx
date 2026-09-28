import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MissingClausesPanel } from '../MissingClausesPanel';
import type { MissingClauseReport } from '../../types/report.types';

describe('MissingClausesPanel', () => {
  it('shows positive message when list is empty', () => {
    render(<MissingClausesPanel missingClauses={[]} />);
    
    expect(screen.getByText(/No required clauses are missing/)).toBeInTheDocument();
  });

  it('renders list of missing clauses when present', () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Termination Notice Clause',
        severity: 'high',
        reason: 'This type of contract requires a termination notice clause',
        explanation: 'Without proper notice requirements, disputes may arise',
        formatted_citation: 'Indian Contract Act, Section 45',
      },
      {
        finding_id: 'uuid-2',
        expected_clause_type: 'Security Deposit Return Clause',
        severity: 'medium',
        reason: 'Missing details about security deposit return',
        explanation: 'Standard practice requires clear deposit return terms',
        formatted_citation: 'Rent Control Act, Section 7',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    expect(screen.getByText('Termination Notice Clause')).toBeInTheDocument();
    expect(screen.getByText('Security Deposit Return Clause')).toBeInTheDocument();
  });

  it('each clause shows severity badge', () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Test Clause',
        severity: 'high',
        reason: 'Test reason',
        explanation: 'Test explanation',
        formatted_citation: 'Test citation',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    const badge = screen.getByText('HIGH');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('shows medium severity badge correctly', () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Test Clause',
        severity: 'medium',
        reason: 'Test reason',
        explanation: 'Test explanation',
        formatted_citation: 'Test citation',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    const badge = screen.getByText('MEDIUM');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('shows low severity badge correctly', () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Test Clause',
        severity: 'low',
        reason: 'Test reason',
        explanation: 'Test explanation',
        formatted_citation: 'Test citation',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    const badge = screen.getByText('LOW');
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('citation displayed correctly when expanded', async () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Test Clause',
        severity: 'high',
        reason: 'Test reason',
        explanation: 'Detailed explanation text',
        formatted_citation: 'Indian Contract Act, Section 10',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    // Initially citation is hidden
    expect(screen.queryByText(/Indian Contract Act/)).not.toBeInTheDocument();
    
    // Click to expand
    await userEvent.click(screen.getByText('Show Details'));
    
    // Now citation should be visible
    expect(screen.getByText(/Indian Contract Act/)).toBeInTheDocument();
    expect(screen.getByText('Detailed explanation text')).toBeInTheDocument();
  });

  it('can collapse expanded details', async () => {
    const missingClauses: MissingClauseReport[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'Test Clause',
        severity: 'high',
        reason: 'Test reason',
        explanation: 'Detailed explanation text',
        formatted_citation: 'Test citation',
      },
    ];

    render(<MissingClausesPanel missingClauses={missingClauses} />);
    
    // Expand
    await userEvent.click(screen.getByText('Show Details'));
    expect(screen.getByText('Detailed explanation text')).toBeInTheDocument();
    
    // Collapse
    await userEvent.click(screen.getByText('Hide Details'));
    expect(screen.queryByText('Detailed explanation text')).not.toBeInTheDocument();
  });
});
