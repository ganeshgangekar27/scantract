import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock localStorage and sessionStorage globally
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

Object.defineProperty(globalThis, 'sessionStorage', {
  value: sessionStorageMock,
  writable: true,
});

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

// Mock matchMedia for components that use theme detection
Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
