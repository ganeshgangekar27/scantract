import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PipelineTracker } from './PipelineTracker';

describe('PipelineTracker - Stage States', () => {
  it('renders classifying stage as active with aria-current="step"', () => {
    render(
      <PipelineTracker
        stage="classifying"
        status="processing"
      />
    );

    const elements = screen.getAllByRole('generic');
    const activeElements = elements.filter(el => el.getAttribute('aria-current') === 'step');
    expect(activeElements.length).toBe(1);
  });

  it('renders detecting_risks stage as active with aria-current="step"', () => {
    render(
      <PipelineTracker
        stage="detecting_risks"
        status="processing"
      />
    );

    const elements = screen.getAllByRole('generic');
    const activeElements = elements.filter(el => el.getAttribute('aria-current') === 'step');
    expect(activeElements.length).toBe(1);
  });

  it('renders completed state with no active stage', () => {
    render(
      <PipelineTracker
        stage="completed"
        status="completed"
      />
    );

    const elements = screen.getAllByRole('generic');
    const activeElements = elements.filter(el => el.getAttribute('aria-current') === 'step');
    expect(activeElements.length).toBe(0);
  });

  it('shows red cross icon for failed stage at classifying', () => {
    render(
      <PipelineTracker
        stage="classifying"
        status="failed"
        failedStage="classifying"
        errorMessage="Test error"
      />
    );

    // Failed stage should show error message
    expect(screen.getByText('Test error')).toBeInTheDocument();
    expect(screen.getByText('Error:')).toBeInTheDocument();
  });
});
