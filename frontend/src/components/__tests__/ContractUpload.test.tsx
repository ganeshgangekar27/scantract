import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { ContractUpload } from '../ContractUpload';

// Mock navigate function at top level
const mockNavigate = vi.fn();

// Mock react-router-dom at top level
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Helper to render component with router
function setup() {
  const user = userEvent.setup();
  const view = render(
    <BrowserRouter>
      <ContractUpload />
    </BrowserRouter>
  );
  return { user, ...view };
}

describe('ContractUpload - TC-1: Render', () => {
  it('should render drop zone with instructions', () => {
    render(
      <BrowserRouter>
        <ContractUpload />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/drag and drop your contract/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /browse files/i })).toBeInTheDocument();
  });
});

describe('ContractUpload - TC-2: File Type Validation - Valid', () => {
  it('should accept PDF files', async () => {
    const { user } = setup();
    const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, file);
    
    expect(screen.queryByText(/only pdf and docx/i)).not.toBeInTheDocument();
  });

  it('should accept DOCX files', async () => {
    const { user } = setup();
    const file = new File(['content'], 'contract.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, file);
    
    expect(screen.queryByText(/only pdf and docx/i)).not.toBeInTheDocument();
  });
});

describe('ContractUpload - TC-3: File Type Validation - Invalid', () => {
  it('should reject TXT files with error message', async () => {
    setup();
    const file = new File(['content'], 'document.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    // Bypass the accept attribute validation by setting files directly
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    // Trigger the change event manually
    const event = new Event('change', { bubbles: true });
    input.dispatchEvent(event);
    
    await waitFor(() => {
      expect(screen.getByText(/only pdf and docx files are supported/i)).toBeInTheDocument();
    });
  });

  it('should reject image files with error message', async () => {
    setup();
    const file = new File(['content'], 'image.jpg', { type: 'image/jpeg' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    // Bypass the accept attribute validation by setting files directly
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    // Trigger the change event manually
    const event = new Event('change', { bubbles: true });
    input.dispatchEvent(event);
    
    await waitFor(() => {
      expect(screen.getByText(/only pdf and docx files are supported/i)).toBeInTheDocument();
    });
  });
});

describe('ContractUpload - TC-4: File Size Validation - Valid', () => {
  it('should accept files under 15MB', async () => {
    const { user } = setup();
    // Create a 10MB file
    const smallFile = new File(['x'.repeat(10 * 1024 * 1024)], 'contract.pdf', {
      type: 'application/pdf'
    });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, smallFile);
    
    expect(screen.queryByText(/file size must be under 15mb/i)).not.toBeInTheDocument();
  });
});

describe('ContractUpload - TC-5: File Size Validation - Invalid', () => {
  it('should reject files over 15MB with error message', async () => {
    const { user } = setup();
    // Create a file object with size property set to 20MB
    const largeFile = new File(['content'], 'large.pdf', { type: 'application/pdf' });
    Object.defineProperty(largeFile, 'size', { value: 20 * 1024 * 1024 }); // 20MB
    
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    await user.upload(input, largeFile);
    
    await waitFor(() => {
      expect(screen.getByText(/file size must be under 15mb/i)).toBeInTheDocument();
    });
  });
});

describe('ContractUpload - TC-6: Upload Flow - Success', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.unstubAllGlobals();
    mockNavigate.mockClear();
  });

  it('should show progress and navigate on successful upload', async () => {
    // Mock XMLHttpRequest with a proper constructor
    class MockXHR {
      public status = 0;
      public responseText = '';
      public upload = {
        addEventListener: vi.fn()
      };
      
      open = vi.fn();
      send = vi.fn();
      setRequestHeader = vi.fn();
      
      addEventListener = vi.fn((event: string, handler: Function) => {
        if (event === 'load') {
          // Simulate successful response
          setTimeout(() => {
            this.status = 200;
            this.responseText = JSON.stringify({
              success: true,
              data: {
                contract_id: 123,  // INTEGER, not UUID
                filename: 'contract.pdf',
                size: 1024,
                upload_timestamp: '2026-08-15T10:30:00Z',
                status: 'uploaded'
              },
              error: null
            });
            handler();
          }, 100);
        }
      });
    }

    vi.stubGlobal('XMLHttpRequest', MockXHR);

    const { user } = setup();
    const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, file);
    
    // Verify upload starts
    await waitFor(() => {
      expect(screen.getByText(/uploading/i)).toBeInTheDocument();
    });
    
    // Wait for completion and navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/report/123');
    }, { timeout: 3000 });
  });
});

describe('ContractUpload - TC-7: Upload Flow - Network Error', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it('should display error message and retry option on network failure', async () => {
    // Mock XMLHttpRequest with error
    class MockXHR {
      public status = 0;
      public responseText = '';
      public upload = {
        addEventListener: vi.fn()
      };
      
      open = vi.fn();
      send = vi.fn();
      setRequestHeader = vi.fn();
      
      addEventListener = vi.fn((event: string, handler: Function) => {
        if (event === 'error') {
          setTimeout(() => {
            handler();
          }, 100);
        }
      });
    }

    vi.stubGlobal('XMLHttpRequest', MockXHR);

    const { user } = setup();
    const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    }, { timeout: 3000 });
    
    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();
    
    // Verify retry clears error
    await user.click(retryButton);
    expect(screen.queryByText(/network error/i)).not.toBeInTheDocument();
  });

  it('should display error message on 500 server error', async () => {
    // Mock XMLHttpRequest with 500 error
    class MockXHR {
      public status = 0;
      public responseText = '';
      public upload = {
        addEventListener: vi.fn()
      };
      
      open = vi.fn();
      send = vi.fn();
      setRequestHeader = vi.fn();
      
      addEventListener = vi.fn((event: string, handler: Function) => {
        if (event === 'load') {
          setTimeout(() => {
            this.status = 500;
            this.responseText = JSON.stringify({
              success: false,
              data: null,
              error: 'Internal server error'
            });
            handler();
          }, 100);
        }
      });
    }

    vi.stubGlobal('XMLHttpRequest', MockXHR);

    const { user } = setup();
    const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/upload contract/i, { selector: 'input' }) as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(screen.getByText(/upload failed with status 500/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

describe('ContractUpload - TC-8: Accessibility', () => {
  it('should be keyboard accessible', async () => {
    const { user } = setup();
    
    // Tab to drop zone
    await user.tab();
    const dropZone = screen.getByRole('button', { name: /upload contract/i });
    expect(dropZone).toHaveFocus();
  });

  it('should have proper aria labels', () => {
    render(
      <BrowserRouter>
        <ContractUpload />
      </BrowserRouter>
    );
    
    const dropZone = screen.getByLabelText(/upload contract/i, { selector: 'input' });
    expect(dropZone).toBeInTheDocument();
    expect(dropZone).toHaveAttribute('aria-label');
  });
});
