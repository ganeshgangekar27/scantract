import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './Badge';

describe('Badge', () => {
  it('renders severity badge', () => {
    render(<Badge variant="severity" severity="high">High Risk</Badge>);
    expect(screen.getByText('High Risk')).toBeInTheDocument();
  });
  
  it('renders status badge', () => {
    render(<Badge variant="status" status="active">Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });
});
