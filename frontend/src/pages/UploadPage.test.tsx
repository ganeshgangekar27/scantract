import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import UploadPage from './UploadPage';

const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock AuthContext
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'test@example.com', full_name: 'Test User' },
    loading: false,
  }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('UploadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderUploadPage = () => {
    return render(
      <MemoryRouter>
        <UploadPage />
      </MemoryRouter>
    );
  };

  it('rejects .txt file with exact error', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const txtFile = new File(['content'], 'test.txt', { type: 'text/plain' });

    await userEvent.upload(input, txtFile);

    expect(await screen.findByText('Only PDF and DOCX files are allowed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyze contract/i })).toBeDisabled();
  });

  it('rejects >15 MB file with exact error', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const largeFile = new File(['x'.repeat(16 * 1024 * 1024)], 'large.pdf', {
      type: 'application/pdf',
    });

    Object.defineProperty(largeFile, 'size', { value: 16 * 1024 * 1024 });

    await userEvent.upload(input, largeFile);

    expect(await screen.findByText('File size must be less than 15 MB')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyze contract/i })).toBeDisabled();
  });

  it('accepts valid PDF and enables Analyze button', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const pdfFile = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });

    await userEvent.upload(input, pdfFile);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /analyze contract/i })).toBeEnabled();
    });
  });

  it('successful upload then polling to completed navigates to /contracts/<id>', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const pdfFile = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });

    await userEvent.upload(input, pdfFile);

    // Mock upload success
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        contract_id: 123,
        filename: 'test.pdf',
        status: 'uploaded',
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    // Mock first poll - processing
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        contract_id: 123,
        filename: 'test.pdf',
        uploaded_at: '2024-01-01T00:00:00Z',
        processing_status: 'processing',
        pipeline_stage: 'classifying',
        failed_stage: null,
        error_message: null,
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    // Mock second poll - completed
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        contract_id: 123,
        filename: 'test.pdf',
        uploaded_at: '2024-01-01T00:00:00Z',
        processing_status: 'completed',
        pipeline_stage: 'completed',
        failed_stage: null,
        error_message: null,
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await userEvent.click(screen.getByRole('button', { name: /analyze contract/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/contracts/123');
    }, { timeout: 5000 });
  });

  it('failed pipeline shows error text and retry button', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const pdfFile = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });

    await userEvent.upload(input, pdfFile);

    // Mock upload success
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        contract_id: 123,
        filename: 'test.pdf',
        status: 'uploaded',
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    // Mock poll - failed
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        contract_id: 123,
        filename: 'test.pdf',
        uploaded_at: '2024-01-01T00:00:00Z',
        processing_status: 'failed',
        pipeline_stage: 'failed',
        failed_stage: 'classifying',
        error_message: 'Classification failed',
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await userEvent.click(screen.getByRole('button', { name: /analyze contract/i }));

    expect(await screen.findByText('Classification failed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload another/i })).toBeInTheDocument();
  });

  it('upload API error is shown', async () => {
    renderUploadPage();

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const pdfFile = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });

    await userEvent.upload(input, pdfFile);

    // Mock upload error
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Server error' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await userEvent.click(screen.getByRole('button', { name: /analyze contract/i }));

    expect(await screen.findByText(/failed to upload/i)).toBeInTheDocument();
  });
});
