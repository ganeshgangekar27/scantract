import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock global fetch to prevent real network calls
(globalThis as any).fetch = vi.fn(() => {
  return Promise.reject(
    new Error('Unmocked fetch call! Use vi.mocked(fetch).mockResolvedValue() to mock this call.')
  );
});

// Mock XMLHttpRequest to prevent real uploads
(globalThis as any).XMLHttpRequest = class MockXMLHttpRequest {
  constructor() {
    throw new Error('Unmocked XMLHttpRequest! Use vi.stubGlobal("XMLHttpRequest", ...) to mock.');
  }
};

