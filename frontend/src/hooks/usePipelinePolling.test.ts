import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePipelinePolling } from './usePipelinePolling';
import * as api from '../lib/api';
import type { ContractListItem } from '../lib/types';

vi.mock('../lib/api');

describe('usePipelinePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('starts polling immediately', async () => {
    const mockData: ContractListItem = {
      contract_id: 1,
      filename: 'test.pdf',
      uploaded_at: '2024-01-01T00:00:00Z',
      processing_status: 'processing',
      pipeline_stage: 'classifying',
      failed_stage: null,
      error_message: null,
      is_sample: false,
    };

    vi.mocked(api.getPipelineStatus).mockResolvedValue(mockData);

    const { result } = renderHook(() => usePipelinePolling(1));

    expect(result.current.loading).toBe(true);
    expect(api.getPipelineStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('stops polling on unmount without further fetch calls', async () => {
    const mockData: ContractListItem = {
      contract_id: 1,
      filename: 'test.pdf',
      uploaded_at: '2024-01-01T00:00:00Z',
      processing_status: 'processing',
      pipeline_stage: 'classifying',
      failed_stage: null,
      error_message: null,
      is_sample: false,
    };

    vi.mocked(api.getPipelineStatus).mockResolvedValue(mockData);

    const { result, unmount } = renderHook(() => usePipelinePolling(1));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(result.current.data).toEqual(mockData);

    const callCountBeforeUnmount = vi.mocked(api.getPipelineStatus).mock.calls.length;

    unmount();

    // Advance time after unmount
    await act(async () => {
      vi.advanceTimersByTime(10000);
      await vi.runAllTimersAsync();
    });

    // Should not have made any more calls after unmount
    expect(vi.mocked(api.getPipelineStatus).mock.calls.length).toBe(callCountBeforeUnmount);
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(api.getPipelineStatus).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => usePipelinePolling(1));

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it('does not poll when contractId is null', () => {
    const { result } = renderHook(() => usePipelinePolling(1));

    expect(result.current.loading).toBe(false);
    expect(api.getPipelineStatus).not.toHaveBeenCalled();

    vi.advanceTimersByTime(10000);
    expect(api.getPipelineStatus).not.toHaveBeenCalled();
  });
});
