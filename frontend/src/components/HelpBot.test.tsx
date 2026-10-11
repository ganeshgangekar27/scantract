import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HelpBot } from './HelpBot';

describe('HelpBot', () => {
  it('renders floating button', () => {
    render(<HelpBot />);
    const button = screen.getByTestId('help-bot-button');
    expect(button).toBeInTheDocument();
  });

  it('opens panel when button is clicked', () => {
    render(<HelpBot />);
    const button = screen.getByTestId('help-bot-button');
    
    // Panel should not be visible initially
    expect(screen.queryByTestId('help-bot-panel')).not.toBeInTheDocument();
    
    // Click to open
    fireEvent.click(button);
    expect(screen.getByTestId('help-bot-panel')).toBeInTheDocument();
  });

  it('closes panel when close button is clicked', () => {
    render(<HelpBot />);
    const button = screen.getByTestId('help-bot-button');
    
    // Open panel
    fireEvent.click(button);
    expect(screen.getByTestId('help-bot-panel')).toBeInTheDocument();
    
    // Close panel
    const closeButton = screen.getByTestId('help-bot-close');
    fireEvent.click(closeButton);
    expect(screen.queryByTestId('help-bot-panel')).not.toBeInTheDocument();
  });

  it('shows answer when topic chip is clicked', () => {
    render(<HelpBot />);
    
    // Open panel
    fireEvent.click(screen.getByTestId('help-bot-button'));
    
    // Click upload topic
    const uploadChip = screen.getByTestId('help-topic-upload');
    fireEvent.click(uploadChip);
    
    // Answer should appear
    expect(screen.getByText(/Upload page/i)).toBeInTheDocument();
  });

  it('shows answer when user types in search box', () => {
    render(<HelpBot />);
    
    // Open panel
    fireEvent.click(screen.getByTestId('help-bot-button'));
    
    // Type in search box
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'file types' } });
    
    // Answer should appear
    expect(screen.getByText(/PDF/i)).toBeInTheDocument();
  });

  it('renders all topic chips', () => {
    render(<HelpBot />);
    
    // Open panel
    fireEvent.click(screen.getByTestId('help-bot-button'));
    
    // Check for topic chips
    expect(screen.getByText('How to upload')).toBeInTheDocument();
    expect(screen.getByText('File types & limits')).toBeInTheDocument();
    expect(screen.getByText('Processing time')).toBeInTheDocument();
    expect(screen.getByText('Risk levels')).toBeInTheDocument();
    expect(screen.getByText('Clause cards')).toBeInTheDocument();
    expect(screen.getByText('Past contracts')).toBeInTheDocument();
    expect(screen.getByText('Failed contracts')).toBeInTheDocument();
    expect(screen.getByText('Delete data')).toBeInTheDocument();
    expect(screen.getByText('Legal disclaimer')).toBeInTheDocument();
  });

  it('clears input when topic chip is clicked', () => {
    render(<HelpBot />);
    
    // Open panel
    fireEvent.click(screen.getByTestId('help-bot-button'));
    
    // Type in search box
    const input = screen.getByPlaceholderText('Ask a question...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'test input' } });
    expect(input.value).toBe('test input');
    
    // Click topic chip
    const uploadChip = screen.getByTestId('help-topic-upload');
    fireEvent.click(uploadChip);
    
    // Input should be cleared
    expect(input.value).toBe('');
  });
});
