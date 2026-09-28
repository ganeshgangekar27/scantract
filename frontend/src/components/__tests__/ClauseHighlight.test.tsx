import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ClauseHighlight } from '../ClauseHighlight';
import type { ClauseWithRisk } from '../../types/report.types';

describe('ClauseHighlight', () => {
  it('renders clause text', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Test clause text',
      has_risk: false,
      risk_severity: null,
      risk_reason: null,
    };

    render(<ClauseHighlight clause={clause} isSelected={false} onClick={vi.fn()} />);
    
    expect(screen.getByText('1.')).toBeInTheDocument();
    expect(screen.getByText('Test clause text')).toBeInTheDocument();
  });

  it('applies correct background color for high severity', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Risky clause',
      has_risk: true,
      risk_severity: 'high',
      risk_reason: 'Very risky',
    };

    const { container } = render(<ClauseHighlight clause={clause} isSelected={false} onClick={vi.fn()} />);
    
    const element = container.firstChild as HTMLElement;
    expect(element).toHaveClass('bg-red-50', 'border-red-500');
  });

  it('applies correct background color for medium severity', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Medium risk clause',
      has_risk: true,
      risk_severity: 'medium',
      risk_reason: 'Moderate risk',
    };

    const { container } = render(<ClauseHighlight clause={clause} isSelected={false} onClick={vi.fn()} />);
    
    const element = container.firstChild as HTMLElement;
    expect(element).toHaveClass('bg-yellow-50', 'border-yellow-500');
  });

  it('applies correct background color for low severity', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Low risk clause',
      has_risk: true,
      risk_severity: 'low',
      risk_reason: 'Minor concern',
    };

    const { container } = render(<ClauseHighlight clause={clause} isSelected={false} onClick={vi.fn()} />);
    
    const element = container.firstChild as HTMLElement;
    expect(element).toHaveClass('bg-blue-50', 'border-blue-500');
  });

  it('no background for clauses without risk', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Safe clause',
      has_risk: false,
      risk_severity: null,
      risk_reason: null,
    };

    const { container } = render(<ClauseHighlight clause={clause} isSelected={false} onClick={vi.fn()} />);
    
    const element = container.firstChild as HTMLElement;
    expect(element).toHaveClass('bg-white');
  });

  it('click handler fires with correct clause_id', async () => {
    const mockClick = vi.fn();
    const clause: ClauseWithRisk = {
      clause_id: 42,
      clause_number: '1.',
      clause_text: 'Clickable risky clause',
      has_risk: true,
      risk_severity: 'high',
      risk_reason: 'Risky',
    };

    render(<ClauseHighlight clause={clause} isSelected={false} onClick={mockClick} />);
    
    await userEvent.click(screen.getByText('Clickable risky clause'));
    
    expect(mockClick).toHaveBeenCalledTimes(1);
  });

  it('selected state shows ring border', () => {
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Selected clause',
      has_risk: true,
      risk_severity: 'high',
      risk_reason: 'Risky',
    };

    const { container } = render(<ClauseHighlight clause={clause} isSelected={true} onClick={vi.fn()} />);
    
    const element = container.firstChild as HTMLElement;
    expect(element).toHaveClass('ring-2', 'ring-blue-500');
  });

  it('does not call onClick for non-risky clauses', async () => {
    const mockClick = vi.fn();
    const clause: ClauseWithRisk = {
      clause_id: 1,
      clause_number: '1.',
      clause_text: 'Safe clause',
      has_risk: false,
      risk_severity: null,
      risk_reason: null,
    };

    render(<ClauseHighlight clause={clause} isSelected={false} onClick={mockClick} />);
    
    await userEvent.click(screen.getByText('Safe clause'));
    
    expect(mockClick).not.toHaveBeenCalled();
  });
});
