/**
 * PipelineTracker displays the contract processing pipeline status.
 * 
 * Shows stages in order with visual states: done, active (with spinner), pending, failed.
 */

import { Button } from './ui';
import { motion, useReducedMotion } from 'framer-motion';
import { CheckCircle2, Loader2, XCircle, Circle } from 'lucide-react';

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
  const shouldReduceMotion = useReducedMotion();

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
    const iconSize = 'w-5 h-5';

    switch (state) {
      case 'done':
        return <CheckCircle2 className={iconSize} />;
      case 'active':
        return <Loader2 className={`${iconSize} ${shouldReduceMotion ? '' : 'animate-spin'}`} />;
      case 'failed':
        return <XCircle className={iconSize} />;
      case 'pending':
      default:
        return <Circle className={iconSize} />;
    }
  };

  const getStageIconContainer = (state: StageState) => {
    const baseClasses = 'flex items-center justify-center w-10 h-10 md:w-12 md:h-12 rounded-full transition-all';

    switch (state) {
      case 'done':
        return `${baseClasses} bg-green-500 text-white dark:bg-green-600`;
      case 'active':
        return `${baseClasses} bg-blue-500 text-white dark:bg-blue-600 ${
          shouldReduceMotion ? '' : 'ring-4 ring-blue-200 dark:ring-blue-900/50 animate-pulse'
        }`;
      case 'failed':
        return `${baseClasses} bg-red-500 text-white dark:bg-red-600`;
      case 'pending':
      default:
        return `${baseClasses} bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500`;
    }
  };

  const getStageTextColor = (state: StageState) => {
    switch (state) {
      case 'done':
        return 'text-green-700 dark:text-green-400';
      case 'active':
        return 'text-blue-700 dark:text-blue-400 font-medium';
      case 'failed':
        return 'text-red-700 dark:text-red-400 font-medium';
      case 'pending':
      default:
        return 'text-gray-500 dark:text-gray-400';
    }
  };

  return (
    <div className="w-full max-w-2xl md:max-w-4xl mx-auto p-6 bg-background-secondary rounded-lg border border-border">
      <h3 className="text-lg font-semibold text-text-primary mb-6">
        Processing Pipeline
      </h3>

      {/* Responsive stepper: vertical on mobile, horizontal on desktop */}
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 md:gap-2">
        {STAGES.map((stageInfo, index) => {
          const state = getStageState(stageInfo.key);
          const isLast = index === STAGES.length - 1;
          const progress = index > 0 && STAGES[index - 1] ? getStageState(STAGES[index - 1].key) === 'done' : false;

          return (
            <div key={stageInfo.key} className="flex flex-1 relative">
              {/* Mobile: Horizontal layout with progress line to the right */}
              {/* Desktop: Vertical layout with progress line below */}
              <div className="flex md:flex-col items-center md:items-center w-full">
                {/* Icon and progress line container */}
                <div className="flex md:flex-col items-center">
                  {/* Stage icon */}
                  <div
                    className={getStageIconContainer(state)}
                    aria-current={state === 'active' ? 'step' : undefined}
                  >
                    {getStageIcon(state)}
                  </div>

                  {/* Progress line - horizontal on mobile, vertical on desktop */}
                  {!isLast && (
                    <div className="flex-1 md:flex-initial flex md:flex-col items-center">
                      {/* Mobile: horizontal line */}
                      <div className="md:hidden h-0.5 w-full min-w-[20px] relative bg-gray-200 dark:bg-gray-700">
                        {progress && (
                          <motion.div
                            className="absolute inset-0 bg-green-500 dark:bg-green-600"
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: 1 }}
                            transition={{ duration: shouldReduceMotion ? 0 : 0.5 }}
                            style={{ transformOrigin: 'left' }}
                          />
                        )}
                      </div>
                      {/* Desktop: vertical line */}
                      <div className="hidden md:block w-0.5 h-8 relative bg-gray-200 dark:bg-gray-700 my-2">
                        {progress && (
                          <motion.div
                            className="absolute inset-0 bg-green-500 dark:bg-green-600"
                            initial={{ scaleY: 0 }}
                            animate={{ scaleY: 1 }}
                            transition={{ duration: shouldReduceMotion ? 0 : 0.5 }}
                            style={{ transformOrigin: 'top' }}
                          />
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Stage label */}
                <div className="flex-1 ml-3 md:ml-0 md:mt-3 md:text-center">
                  <p className={`text-sm ${getStageTextColor(state)}`}>
                    {stageInfo.label}
                  </p>

                  {/* Error message - show below the label */}
                  {state === 'failed' && errorMessage && (
                    <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 rounded text-sm text-left">
                      <p className="font-medium text-red-800 dark:text-red-400 mb-1">Error:</p>
                      <p className="text-red-700 dark:text-red-300">{errorMessage}</p>
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
