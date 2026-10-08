/**
 * PipelineTracker displays the contract processing pipeline status.
 * 
 * Shows stages in order with visual states: done, active (with spinner), pending, failed.
 */

import { Button } from './ui';

export interface PipelineTrackerProps {
  stage: string | null;
  status: string;
  failedStage?: string | null;
  errorMessage?: string | null;
  onRetry?: () => void;
}

interface StageInfo {
  key: string;
  label: string;
}

// Pipeline stages in order (from orchestrator.py)
const STAGES: StageInfo[] = [
  { key: 'classifying', label: 'Classifying clauses' },
  { key: 'classified', label: 'Classification complete' },
  { key: 'detecting_risks', label: 'Detecting risks' },
  { key: 'risks_detected', label: 'Risk detection complete' },
  { key: 'generating_explanations', label: 'Generating explanations' },
  { key: 'explanations_generated', label: 'Explanations complete' },
  { key: 'completed', label: 'Analysis complete' },
];

type StageState = 'done' | 'active' | 'pending' | 'failed';

export function PipelineTracker({
  stage,
  status,
  failedStage,
  errorMessage,
  onRetry,
}: PipelineTrackerProps) {
  const getStageState = (stageKey: string): StageState => {
    // If failed, mark the failed stage
    if (status === 'failed' && failedStage === stageKey) {
      return 'failed';
    }

    // If completed, all stages are done
    if (status === 'completed' || stage === 'completed') {
      return 'done';
    }

    // Find current stage index
    const currentIndex = STAGES.findIndex((s) => s.key === stage);
    const thisIndex = STAGES.findIndex((s) => s.key === stageKey);

    if (currentIndex === -1) {
      // Unknown stage, treat as pending
      return 'pending';
    }

    if (thisIndex < currentIndex) {
      return 'done';
    }

    if (thisIndex === currentIndex) {
      return 'active';
    }

    return 'pending';
  };

  const getStageIcon = (state: StageState) => {
    switch (state) {
      case 'done':
        return (
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-success text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        );

      case 'active':
        return (
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
        );

      case 'failed':
        return (
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-severity-high text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        );

      case 'pending':
      default:
        return (
          <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 border-border bg-background-secondary">
            <div className="w-2 h-2 rounded-full bg-text-tertiary" />
          </div>
        );
    }
  };

  const getStageTextColor = (state: StageState) => {
    switch (state) {
      case 'done':
        return 'text-success';
      case 'active':
        return 'text-primary font-medium';
      case 'failed':
        return 'text-severity-high font-medium';
      case 'pending':
      default:
        return 'text-text-tertiary';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-background-secondary rounded-lg border border-border">
      <h3 className="text-lg font-semibold text-text-primary mb-6">
        Processing Pipeline
      </h3>

      <div className="space-y-4">
        {STAGES.map((stageInfo, index) => {
          const state = getStageState(stageInfo.key);
          const isLast = index === STAGES.length - 1;

          return (
            <div key={stageInfo.key}>
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center">
                  {getStageIcon(state)}
                  {!isLast && (
                    <div className={`w-0.5 h-8 mt-2 ${state === 'done' ? 'bg-success' : 'bg-border'}`} />
                  )}
                </div>

                <div className="flex-1 pt-1">
                  <p className={`text-sm ${getStageTextColor(state)}`}>
                    {stageInfo.label}
                  </p>

                  {state === 'failed' && errorMessage && (
                    <div className="mt-2 p-3 bg-severity-high-bg border border-severity-high-border rounded text-sm text-severity-high">
                      <p className="font-medium mb-1">Error:</p>
                      <p>{errorMessage}</p>
                      {onRetry && (
                        <Button onClick={onRetry} variant="secondary" className="mt-3">
                          Try again
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
