/**
 * usePipelinePolling hook polls pipeline status for a contract.
 * 
 * - Polls every 3000ms initially
 * - Stops on completed or failed status
 * - Backs off to 6000ms after 40 polls
 * - Stops after 10 minutes with timeout state
 * - Cleans up on unmount
 */

import { useEffect, useState, useRef } from 'react';
import { getPipelineStatus } from '../lib/api';
import type { ContractListItem } from '../lib/types';

const INITIAL_INTERVAL = 3000; // 3 seconds
const BACKOFF_INTERVAL = 6000; // 6 seconds
const BACKOFF_AFTER_POLLS = 40; // Back off after 40 polls (2 minutes)
const MAX_DURATION = 10 * 60 * 1000; // 10 minutes

interface UsePipelinePollingResult {
  data: ContractListItem | null;
  loading: boolean;
  error: string | null;
  isTimeout: boolean;
}

export function usePipelinePolling(contractId: number | null): UsePipelinePollingResult {
  const [data, setData] = useState<ContractListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTimeout, setIsTimeout] = useState(false);

  const pollCountRef = useRef(0);
  const startTimeRef = useRef<number>(Date.now());
  const intervalIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!contractId) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    startTimeRef.current = Date.now();
    pollCountRef.current = 0;

    const poll = async () => {
      if (!isMounted) return;

      // Check for timeout (10 minutes)
      const elapsed = Date.now() - startTimeRef.current;
      if (elapsed >= MAX_DURATION) {
        setIsTimeout(true);
        setLoading(false);
        if (intervalIdRef.current) {
          clearInterval(intervalIdRef.current);
          intervalIdRef.current = null;
        }
        return;
      }

      try {
        const status = await getPipelineStatus(contractId);

        if (!isMounted) return;

        setData(status);
        setError(null);
        setLoading(false);

        // Stop polling if completed or failed
        if (status.processing_status === 'completed' || status.processing_status === 'failed') {
          if (intervalIdRef.current) {
            clearInterval(intervalIdRef.current);
            intervalIdRef.current = null;
          }
          return;
        }

        // Increment poll count
        pollCountRef.current += 1;

        // Back off to slower interval after 40 polls
        if (pollCountRef.current === BACKOFF_AFTER_POLLS && intervalIdRef.current) {
          clearInterval(intervalIdRef.current);
          intervalIdRef.current = setInterval(poll, BACKOFF_INTERVAL);
        }
      } catch (err) {
        if (!isMounted) return;

        setError(err instanceof Error ? err.message : 'Failed to fetch pipeline status');
        setLoading(false);

        // Stop polling on error
        if (intervalIdRef.current) {
          clearInterval(intervalIdRef.current);
          intervalIdRef.current = null;
        }
      }
    };

    // Start polling immediately
    poll();

    // Set up interval for subsequent polls
    intervalIdRef.current = setInterval(poll, INITIAL_INTERVAL);

    // Cleanup
    return () => {
      isMounted = false;
      if (intervalIdRef.current) {
        clearInterval(intervalIdRef.current);
        intervalIdRef.current = null;
      }
    };
  }, [contractId]);

  return { data, loading, error, isTimeout };
}
