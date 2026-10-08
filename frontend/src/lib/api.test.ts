import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiRequest, ApiError } from './api';

describe('api.ts', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });
  
  afterEach(() => {
    vi.restoreAllMocks();
  });
  
  it('attaches Authorization header when token exists', async () => {
    const mockLocalStorage = {
      getItem: vi.fn(() => 'test-token-123'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    Object.defineProperty(window, 'localStorage', { value: mockLocalStorage, writable: true });
    
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ data: 'test' }),
    });
    
    await apiRequest('/api/test');
    
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer test-token-123',
        }),
      })
    );
  });
  
  it('parses FastAPI validation errors (422)', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 422,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        detail: [
          { loc: ['body', 'email'], msg: 'Invalid email', type: 'value_error' },
          { loc: ['body', 'password'], msg: 'Too short', type: 'value_error' },
        ],
      }),
    });
    
    try {
      await apiRequest('/api/test');
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiError = err as ApiError;
      expect(apiError.status).toBe(422);
      expect(apiError.fieldErrors).toEqual({
        email: ['Invalid email'],
        password: ['Too short'],
      });
    }
  });
  
  it('parses {success, data, error} envelope', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true, data: { id: 1 } }),
    });
    
    const result = await apiRequest('/api/test');
    expect(result).toEqual({ id: 1 });
  });
});
