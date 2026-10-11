import { describe, it, expect, vi, beforeEach } from 'vitest';
import { deleteContract, retryContract, deleteMyData } from './api';

describe('API functions', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    // Mock localStorage.getItem to return test token
    (localStorage.getItem as any) = vi.fn((key: string) => {
      if (key === 'scantract_token') return 'test-token-123';
      return null;
    });
  });

  describe('deleteContract', () => {
    it('sends DELETE request with Authorization header', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true }),
      });

      await deleteContract(123);

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as any).mock.calls[0];
      expect(callArgs[0]).toContain('/api/contracts/123');
      expect(callArgs[1].method).toBe('DELETE');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token-123');
    });

    it('uses correct URL', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true }),
      });

      await deleteContract(456);

      const callArgs = (global.fetch as any).mock.calls[0];
      expect(callArgs[0]).toContain('/api/contracts/456');
    });
  });

  describe('retryContract', () => {
    it('sends POST request with Authorization header', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { contract_id: 789 } }),
      });

      await retryContract(789);

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as any).mock.calls[0];
      expect(callArgs[0]).toContain('/api/contracts/789/retry');
      expect(callArgs[1].method).toBe('POST');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token-123');
    });

    it('returns contract_id from response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { contract_id: 999 } }),
      });

      const result = await retryContract(999);

      expect(result).toEqual({ contract_id: 999 });
    });

    it('uses correct URL', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { contract_id: 111 } }),
      });

      await retryContract(111);

      const callArgs = (global.fetch as any).mock.calls[0];
      expect(callArgs[0]).toContain('/api/contracts/111/retry');
    });
  });

  describe('deleteMyData', () => {
    it('sends DELETE request to /api/auth/me/data with Authorization header', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { deleted_contracts: 5 } }),
      });

      await deleteMyData();

      expect(global.fetch).toHaveBeenCalled();
      const callArgs = (global.fetch as any).mock.calls[0];
      expect(callArgs[0]).toContain('/api/auth/me/data');
      expect(callArgs[1].method).toBe('DELETE');
      expect(callArgs[1].headers.Authorization).toBe('Bearer test-token-123');
    });

    it('returns deleted_contracts count', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: { deleted_contracts: 3 } }),
      });

      const result = await deleteMyData();

      expect(result).toEqual({ deleted_contracts: 3 });
    });
  });

  describe('URL formation', () => {
    it('uses relative URLs starting with /api, not absolute URLs', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true }),
      });

      await deleteContract(123);

      const callArgs = (global.fetch as any).mock.calls[0];
      const url = callArgs[0];
      
      // Must start with /api (relative URL), NOT http:// or https://
      expect(url).toMatch(/^\/api/);
      expect(url).not.toMatch(/^https?:\/\//);
    });
  });
});
