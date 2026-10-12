import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SeverityBar } from '../SeverityBar';

describe('SeverityBar', () => {
  it('renders segments with correct widths for counts 2/1/1', () => {
    render(<SeverityBar high={2} medium={1} low={1} />);
    
    const bar = screen.getByTestId('severity-bar');
    expect(bar).toBeInTheDocument();
    
    const segments = bar.querySelectorAll('div');
    expect(segments).toHaveLength(3);
    
    // High: 2/4 = 50%
    expect(segments[0]).toHaveStyle({ width: '50%' });
    expect(segments[0]).toHaveClass('bg-severity-high');
    
    // Medium: 1/4 = 25%
    expect(segments[1]).toHaveStyle({ width: '25%' });
    expect(segments[1]).toHaveClass('bg-severity-medium');
    
    // Low: 1/4 = 25%
    expect(segments[2]).toHaveStyle({ width: '25%' });
    expect(segments[2]).toHaveClass('bg-severity-low');
  });

  it('does not render segment with zero count', () => {
    render(<SeverityBar high={3} medium={0} low={1} />);
    
    const bar = screen.getByTestId('severity-bar');
    const segments = bar.querySelectorAll('div');
    
    // Only 2 segments (high and low, no medium)
    expect(segments).toHaveLength(2);
    expect(segments[0]).toHaveClass('bg-severity-high');
    expect(segments[1]).toHaveClass('bg-severity-low');
  });

  it('renders nothing when total is 0', () => {
    const { container } = render(<SeverityBar high={0} medium={0} low={0} />);
    
    expect(screen.queryByTestId('severity-bar')).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });

  it('has exact aria-label text', () => {
    render(<SeverityBar high={2} medium={1} low={1} />);
    
    const bar = screen.getByTestId('severity-bar');
    expect(bar).toHaveAttribute('aria-label', '2 high, 1 medium, 1 low');
  });

  it('renders role="img"', () => {
    render(<SeverityBar high={1} medium={1} low={1} />);
    
    const bar = screen.getByTestId('severity-bar');
    expect(bar).toHaveAttribute('role', 'img');
  });
});
