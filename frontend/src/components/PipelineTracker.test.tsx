import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PipelineTracker } from './PipelineTracker';

describe('PipelineTracker', () => {
  it('renders classifying stage as active', () => {
    render(
      <PipelineTracker
        stage="classifying"
        status="processing"
      />
    );

    expect(screen.getByText('Classifying clauses')).toBeInTheDocument();
    expect(screen.getByText('Processing Pipeline')).toBeInTheDocument();
  });

  it('renders classified stage as active', () => {
    render(
      <PipelineTracker
        stage="classified"
        status="processing"
      />
    );

    expect(screen.getByText('Classification complete')).toBeInTheDocument();
  });

  it('renders detecting_risks stage as active', () => {
    render(
      <PipelineTracker
        stage="detecting_risks"
        status="processing"
      />
    );

    expect(screen.getByText('Detecting risks')).toBeInTheDocument();
  });

  it('renders risks_detected stage as active', () => {
    render(
      <PipelineTracker
        stage="risks_detected"
        status="processing"
      />
    );

    expect(screen.getByText('Risk detection complete')).toBeInTheDocument();
  });

  it('renders generating_explanations stage as active', () => {
    render(
      <PipelineTracker
        stage="generating_explanations"
        status="processing"
      />
    );

    expect(screen.getByText('Generating explanations')).toBeInTheDocument();
  });

  it('renders explanations_generated stage as active', () => {
    render(
      <PipelineTracker
        stage="explanations_generated"
        status="processing"
      />
    );

    expect(screen.getByText('Explanations complete')).toBeInTheDocument();
  });

  it('renders completed state with all stages done', () => {
    render(
      <PipelineTracker
        stage="completed"
        status="completed"
      />
    );

    expect(screen.getByText('Analysis complete')).toBeInTheDocument();
    expect(screen.getByText('Classifying clauses')).toBeInTheDocument();
  });

  it('renders failed state at classifying stage with error message and retry button', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();

    render(
      <PipelineTracker
        stage="failed"
        status="failed"
        failedStage="classifying"
        errorMessage="Daily AI request limit reached. Please try again tomorrow."
        onRetry={onRetry}
      />
    );

    expect(screen.getByText('Error:')).toBeInTheDocument();
    expect(screen.getByText('Daily AI request limit reached. Please try again tomorrow.')).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /try again/i });
    expect(retryButton).toBeInTheDocument();

    await user.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders failed state at detecting_risks stage with specific error', () => {
    render(
      <PipelineTracker
        stage="failed"
        status="failed"
        failedStage="detecting_risks"
        errorMessage="Risk detection failed: No clauses found"
      />
    );

    expect(screen.getByText('Risk detection failed: No clauses found')).toBeInTheDocument();
  });

  it('renders unknown stage without crashing', () => {
    render(
      <PipelineTracker
        stage="unknown_stage"
        status="processing"
      />
    );

    // Should still render all stages
    expect(screen.getByText('Classifying clauses')).toBeInTheDocument();
    expect(screen.getByText('Analysis complete')).toBeInTheDocument();
  });

  it('renders null stage without crashing', () => {
    render(
      <PipelineTracker
        stage={null}
        status="uploaded"
      />
    );

    expect(screen.getByText('Processing Pipeline')).toBeInTheDocument();
  });

  it('shows retry button only when onRetry prop is provided', () => {
    const { rerender } = render(
      <PipelineTracker
        stage="failed"
        status="failed"
        failedStage="classifying"
        errorMessage="Test error"
      />
    );

    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();

    rerender(
      <PipelineTracker
        stage="failed"
        status="failed"
        failedStage="classifying"
        errorMessage="Test error"
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });
});
