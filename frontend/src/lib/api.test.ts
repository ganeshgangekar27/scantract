import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listContracts, getReport, downloadReportPdf, uploadContract, getPipelineStatus, ApiError } from './api';
import type { ContractListItem, Report, UploadResponse } from './types';

describe('API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
    vi.mocked(localStorage.getItem).mockReturnValue('test-token');
    vi.mocked(localStorage.setItem).mockClear();
    vi.mocked(localStorage.removeItem).mockClear();
  });

  describe('listContracts', () => {
    it('fetches contract list with auth header', async () => {
      const mockContracts: ContractListItem[] = [
        {
          contract_id: 1,
          filename: 'test.pdf',
          uploaded_at: '2024-01-01T00:00:00Z',
          processing_status: 'completed',
          pipeline_stage: null,
          failed_stage: null,
          error_message: null,
          is_sample: false,
        },
      ];

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockContracts,
      });

      const result = await listContracts();

      expect(globalThis.fetch).toHaveBeenCalled();
      const callArgs = (globalThis.fetch as any).mock.calls[0];
      expect(callArgs[0]).toBe('/api/contracts/list');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token');
      expect(result).toEqual(mockContracts);
    });

    it('throws ApiError on failure', async () => {
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(listContracts()).rejects.toThrow(ApiError);
    });
  });

  describe('getReport', () => {
    it('fetches report with auth header', async () => {
      const mockReport: Report = {
        contract_id: 46,
        filename: 'test.pdf',
        upload_date: '2024-01-01T00:00:00Z',
        all_clauses: [],
        risky_clauses: [],
        missing_clauses: [],
        risk_summary: {
          total_clauses: 10,
          risky_clauses_count: 0,
          missing_clauses_count: 0,
          high_severity_count: 0,
          medium_severity_count: 0,
          low_severity_count: 0,
          overall_risk_level: 'none',
        },
        legal_references: [],
      };

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: mockReport, error: null }),
      });

      const result = await getReport(46);

      expect(globalThis.fetch).toHaveBeenCalled();
      const callArgs = (globalThis.fetch as any).mock.calls[0];
      expect(callArgs[0]).toBe('/api/contracts/46/report');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token');
      expect(result).toEqual(mockReport);
    });

    it('unwraps success envelope', async () => {
      const mockReport: Report = {
        contract_id: 46,
        filename: 'test.pdf',
        upload_date: '2024-01-01T00:00:00Z',
        all_clauses: [],
        risky_clauses: [],
        missing_clauses: [],
        risk_summary: {
          total_clauses: 0,
          risky_clauses_count: 0,
          missing_clauses_count: 0,
          high_severity_count: 0,
          medium_severity_count: 0,
          low_severity_count: 0,
          overall_risk_level: 'none',
        },
        legal_references: [],
      };

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: mockReport, error: null }),
      });

      const result = await getReport(46);
      expect(result.contract_id).toBe(46);
    });
  });

  describe('downloadReportPdf', () => {
    it('fetches PDF blob with auth header', async () => {
      const mockBlob = new Blob(['fake pdf'], { type: 'application/pdf' });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/pdf' }),
        blob: async () => mockBlob,
      });

      const result = await downloadReportPdf(46);

      expect(globalThis.fetch).toHaveBeenCalled();
      const callArgs = (globalThis.fetch as any).mock.calls[0];
      expect(callArgs[0]).toBe('/api/contracts/46/report/pdf');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token');
      expect(result).toBeInstanceOf(Blob);
    });

    it('throws ApiError on JSON error response', async () => {
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Contract not found' }),
      });

      await expect(downloadReportPdf(999)).rejects.toThrow('Contract not found');
    });

    it('throws ApiError on non-JSON error response', async () => {
      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'text/plain' }),
      });

      await expect(downloadReportPdf(46)).rejects.toThrow('HTTP 500');
    });
  });

  describe('uploadContract', () => {
    it('uploads file with FormData and auth header', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse: UploadResponse = {
        contract_id: 123,
        filename: 'test.pdf',
        size: 1024,
        upload_timestamp: '2024-01-01T00:00:00Z',
        status: 'uploaded',
      };

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockResponse,
      });

      const result = await uploadContract(mockFile);

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/contracts/upload',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
      
      // Check auth header was set
      const callArgs = (globalThis.fetch as any).mock.calls[0][1];
      expect(callArgs.headers.Authorization).toBe('Bearer test-token');
      
      expect(result).toEqual(mockResponse);
    });

    it('does not set Content-Type header manually', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse: UploadResponse = {
        contract_id: 123,
        filename: 'test.pdf',
        size: 1024,
        upload_timestamp: '2024-01-01T00:00:00Z',
        status: 'uploaded',
      };

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockResponse,
      });

      await uploadContract(mockFile);

      const callArgs = (globalThis.fetch as any).mock.calls[0][1];
      // Ensure Content-Type is not set (browser will set it with boundary)
      expect(callArgs.headers['Content-Type']).toBeUndefined();
    });

    it('throws ApiError on upload failure', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'File too large' }),
      });

      await expect(uploadContract(mockFile)).rejects.toThrow('File too large');
    });
  });

  describe('getPipelineStatus', () => {
    it('fetches contract list and finds contract by ID', async () => {
      const mockContracts: ContractListItem[] = [
        {
          contract_id: 1,
          filename: 'test1.pdf',
          uploaded_at: '2024-01-01T00:00:00Z',
          processing_status: 'completed',
          pipeline_stage: null,
          failed_stage: null,
          error_message: null,
          is_sample: false,
        },
        {
          contract_id: 2,
          filename: 'test2.pdf',
          uploaded_at: '2024-01-02T00:00:00Z',
          processing_status: 'processing',
          pipeline_stage: 'segmentation',
          failed_stage: null,
          error_message: null,
          is_sample: false,
        },
      ];

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockContracts,
      });

      const result = await getPipelineStatus(2);

      expect(result.contract_id).toBe(2);
      expect(result.processing_status).toBe('processing');
      expect(result.pipeline_stage).toBe('segmentation');
    });

    it('throws ApiError when contract not found', async () => {
      const mockContracts: ContractListItem[] = [
        {
          contract_id: 1,
          filename: 'test1.pdf',
          uploaded_at: '2024-01-01T00:00:00Z',
          processing_status: 'completed',
          pipeline_stage: null,
          failed_stage: null,
          error_message: null,
          is_sample: false,
        },
      ];

      (globalThis.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockContracts,
      });

      await expect(getPipelineStatus(999)).rejects.toThrow('Contract 999 not found');
    });
  });
});
