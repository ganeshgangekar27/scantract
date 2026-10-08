import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmptyState } from './EmptyState';
import { FileText } from 'lucide-react';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(
      <EmptyState 
        icon={FileText} 
        title="No contracts" 
        description="Upload your first contract" 
      />
    );
    expect(screen.getByText('No contracts')).toBeInTheDocument();
    expect(screen.getByText('Upload your first contract')).toBeInTheDocument();
  });
  
  it('renders action button when provided', async () => {
    const handleAction = vi.fn();
    render(
      <EmptyState 
        icon={FileText} 
        title="No contracts" 
        description="Upload your first contract"
        action={{ label: 'Upload', onClick: handleAction }}
      />
    );
    
    await userEvent.click(screen.getByText('Upload'));
    expect(handleAction).toHaveBeenCalledOnce();
  });
});
