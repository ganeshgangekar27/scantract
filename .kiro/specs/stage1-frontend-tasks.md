# Stage 1 Frontend Tasks - Contract Upload Page

## Context

**Current state:**
- ✅ Backend FastAPI app exists at `backend/app/main.py` with real database session factory
- ✅ Backend Stages 3-9 implemented and tested with synthetic data
- ❌ `frontend/` directory is completely empty - no Vite project scaffolded yet
- ❌ Stage 2 (document processing backend) does NOT exist yet - no `POST /api/contracts/upload` endpoint
- ❌ Stage 1 (this spec) is **FRONTEND ONLY** - building the upload UI, not the backend endpoint

**Critical notes:**

1. **contract_id is INTEGER everywhere** - TypeScript response interface must use `number`, not string/UUID
2. **Stage 2's upload endpoint doesn't exist yet** - this is intentional and expected. Build the UI component fully functional, test it with **MOCKED fetch calls** (mock 200 success with fake contract_id, mock 500/network errors). The real endpoint will be wired in Stage 2 next.
3. **This spec is frontend-only** - no backend code, no upload endpoint implementation. Focus: React component, validation, progress/error states, routing, tests with mocks.

---

## Tasks

### Task 1: Scaffold Vite + React + TypeScript Project

**Goal:** Initialize the frontend project from scratch in the empty `frontend/` directory.

**Steps:**

1. **Run Vite scaffolding:**
   ```bash
   cd d:\scantract
   npm create vite@latest frontend -- --template react-ts
   ```
   
   **Important:** Use `frontend` as the project name to scaffold into the existing empty directory.

2. **Install base dependencies:**
   ```bash
   cd frontend
   npm install
   npm install react-router-dom
   ```
   
   **Decision:** Use native `fetch` API (no axios) - one less dependency, modern browsers support it fully, sufficient for our needs.

3. **Install Tailwind CSS:**
   
   Follow Vite integration guide:
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```
   
   **Update `tailwind.config.js`:**
   ```js
   /** @type {import('tailwindcss').Config} */
   export default {
     content: [
       "./index.html",
       "./src/**/*.{js,ts,jsx,tsx}",
     ],
     theme: {
       extend: {},
     },
     plugins: [],
   }
   ```
   
   **Update `src/index.css`:**
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

4. **Verify dev server starts:**
   ```bash
   npm run dev
   ```
   
   **Expected:** Server starts on `http://localhost:5173`, default Vite React page renders without errors.
   
   **Action:** Open browser, confirm "Vite + React" page loads, then stop the server.

5. **Clean up default scaffolding:**
   - Delete `src/App.css` (using Tailwind instead)
   - Delete `src/assets/` directory (not needed yet)
   - Clear default content from `src/App.tsx` (will rebuild in Task 5)

**Verification checklist:**
- ✅ `frontend/package.json` exists with React 18.x, TypeScript, Vite, react-router-dom, Tailwind
- ✅ `frontend/tailwind.config.js` and `frontend/postcss.config.js` exist
- ✅ `npm run dev` starts without errors
- ✅ TypeScript compilation works (`npm run build` succeeds)

---

### Task 2: Create TypeScript Types

**File:** `frontend/src/types/upload.types.ts`

Define interfaces for upload component state and API response.

**Requirements:**

```typescript
/**
 * Upload component state interface.
 */
export interface UploadState {
  file: File | null;
  uploading: boolean;
  uploadProgress: number;  // 0-100
  processing: boolean;
  error: string | null;
}

/**
 * Backend upload response shape.
 * 
 * NOTE: contract_id is INTEGER (number), not UUID string.
 * Matches backend contracts table schema.
 */
export interface UploadResponse {
  contract_id: number;  // INTEGER from database
  filename: string;
  size: number;  // bytes
  upload_timestamp: string;  // ISO datetime
  status: string;  // e.g., "uploaded", "processing"
}

/**
 * Standard API response envelope.
 * 
 * Used across all ScanTract backend endpoints.
 */
export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

/**
 * File validation result.
 */
export interface ValidationResult {
  isValid: boolean;
  error: string | null;
}
```

**Notes:**
- `contract_id` typed as `number` to match backend INTEGER type
- `APIResponse<T>` generic matches backend envelope pattern from Stage 8/9
- `ValidationResult` helper for validation logic return values

---

### Task 3: Implement ContractUpload Component

**File:** `frontend/src/components/ContractUpload.tsx`

Main upload component implementing all functional requirements from original spec.

**Requirements:**

**FR-1: File Input Interface**
- Drag-and-drop zone with visual feedback:
  - Default state: dashed border, gray background
  - Hover state: blue border, light blue background
  - Active drop state: solid blue border, brighter blue background
- "Browse Files" button as alternative
- Clear instructions text: "Drag and drop your contract here or click to browse"
- File input accepts `.pdf,.docx` extensions

**FR-2: File Type Validation**
```typescript
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
];

function validateFileType(file: File): ValidationResult {
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  const isValidExtension = ALLOWED_EXTENSIONS.includes(extension);
  const isValidMimeType = ALLOWED_MIME_TYPES.includes(file.type);
  
  if (!isValidExtension || !isValidMimeType) {
    return {
      isValid: false,
      error: 'Only PDF and DOCX files are supported'
    };
  }
  
  return { isValid: true, error: null };
}
```

**FR-3: File Size Validation**
```typescript
const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB in bytes

function validateFileSize(file: File): ValidationResult {
  if (file.size > MAX_FILE_SIZE) {
    return {
      isValid: false,
      error: 'File size must be under 15MB'
    };
  }
  
  return { isValid: true, error: null };
}
```

**FR-4: Upload Progress**
- Show progress bar during upload (0-100%)
- Use `XMLHttpRequest` for progress tracking:
  ```typescript
  const xhr = new XMLHttpRequest();
  
  xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) {
      const percentComplete = (e.loaded / e.total) * 100;
      setUploadProgress(Math.round(percentComplete));
    }
  });
  ```
- Display "Uploading... X%" during file transfer
- After upload completes (200 response), show "Processing..." state

**FR-5: Backend Integration**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        setUploadProgress(Math.round(percent));
      }
    });
    
    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        const response: APIResponse<UploadResponse> = JSON.parse(xhr.responseText);
        if (response.success && response.data) {
          resolve(response.data);
        } else {
          reject(new Error(response.error || 'Upload failed'));
        }
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    });
    
    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'));
    });
    
    xhr.open('POST', `${API_BASE_URL}/api/contracts/upload`);
    xhr.send(formData);
  });
}
```

**FR-6: Navigation**
```typescript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

// On successful upload:
const handleUploadSuccess = (response: UploadResponse) => {
  setProcessing(true);
  // Navigate to report view with contract_id as number
  navigate(`/report/${response.contract_id}`);
};
```

**Component structure:**
```tsx
interface ContractUploadProps {
  onUploadComplete?: (contractId: number) => void;
}

export const ContractUpload: React.FC<ContractUploadProps> = ({ onUploadComplete }) => {
  const [state, setState] = useState<UploadState>({
    file: null,
    uploading: false,
    uploadProgress: 0,
    processing: false,
    error: null
  });
  
  const navigate = useNavigate();
  
  // Event handlers
  const handleDrop = (e: React.DragEvent) => { /* ... */ };
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => { /* ... */ };
  const handleUpload = async () => { /* ... */ };
  const handleRetry = () => { /* ... */ };
  
  // Validation
  const validateFile = (file: File): ValidationResult => { /* ... */ };
  
  return (
    <div className="container mx-auto max-w-2xl p-8">
      {/* Drop zone */}
      {/* Progress bar */}
      {/* Error display */}
      {/* Processing state */}
    </div>
  );
};
```

**Styling (Tailwind classes):**

Drop zone states:
- Default: `border-2 border-dashed border-gray-300 bg-gray-50 rounded-lg p-12`
- Hover: `border-blue-400 bg-blue-50`
- Active drag: `border-blue-600 bg-blue-100 border-solid`
- Error: `border-red-400 bg-red-50`

Progress bar:
- Container: `w-full bg-gray-200 rounded-full h-3 mb-4`
- Fill: `bg-blue-600 h-3 rounded-full transition-all duration-300`
- Percentage text: `text-sm text-gray-700 mb-2`

Error message:
- Container: `bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded mb-4`
- Retry button: `bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded`

**Accessibility:**
- Drop zone has `role="button"` and `tabIndex={0}`
- Keyboard handler for Enter/Space to trigger file browser
- Aria labels: `aria-label="Upload contract file"` on drop zone
- File input has `id` linked to label for screen readers
- Error messages have `role="alert"` for screen reader announcements

---

### Task 4: Create Environment Configuration Files

**File 1:** `frontend/.env.development`
```env
VITE_API_BASE_URL=http://localhost:8000
```

**File 2:** `frontend/.env.production`
```env
# Production API URL - update when deploying
VITE_API_BASE_URL=https://api.scantract.com
```

**File 3:** `frontend/.env.example`
```env
# ScanTract Frontend Environment Variables
# Copy this to .env.development and update values

# Backend API base URL (no trailing slash)
VITE_API_BASE_URL=http://localhost:8000
```

**Verification:**
- Add `.env.development` and `.env.production` to `.gitignore` (Vite does this by default)
- Ensure `.env.example` is committed to git
- Verify `import.meta.env.VITE_API_BASE_URL` is accessible in components

---

### Task 5: Wire Up React Router

**File:** `frontend/src/App.tsx`

Set up routing with react-router-dom.

**Requirements:**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ContractUpload } from './components/ContractUpload';
import { ReportPlaceholder } from './pages/ReportPlaceholder';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">ScanTract</h1>
            <p className="text-sm text-gray-600">Contract Risk Analysis</p>
          </div>
        </header>
        
        {/* Routes */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ContractUpload />} />
            <Route path="/upload" element={<Navigate to="/" replace />} />
            <Route path="/report/:contractId" element={<ReportPlaceholder />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

**Additional File:** `frontend/src/pages/ReportPlaceholder.tsx`

Placeholder page for Stage 9's eventual ReportView component.

```tsx
import { useParams } from 'react-router-dom';

export const ReportPlaceholder: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  
  // Parse as number to verify type correctness
  const contractIdNum = contractId ? Number(contractId) : null;
  
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Report View (Placeholder)
        </h2>
        <p className="text-gray-600 mb-4">
          This page will display the contract risk report once Stage 9 frontend is implemented.
        </p>
        
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <p className="text-sm text-gray-700">
            <strong>Contract ID:</strong> {contractIdNum}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Type:</strong> {typeof contractIdNum === 'number' ? 'number ✓' : 'ERROR: not a number'}
          </p>
        </div>
        
        <div className="mt-6">
          <a href="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Upload
          </a>
        </div>
      </div>
    </div>
  );
};
```

**Verification:**
- Navigate to `/` → ContractUpload component renders
- Navigate to `/upload` → redirects to `/`
- Navigate to `/report/123` → ReportPlaceholder shows "Contract ID: 123" and "Type: number ✓"
- Navigate to `/invalid-route` → redirects to `/`

---

### Task 6: Write Component Tests

**File:** `frontend/src/components/__tests__/ContractUpload.test.tsx`

Unit tests using Vitest + React Testing Library.

**Setup:**

1. **Install testing dependencies:**
   ```bash
   npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest jsdom
   ```

2. **Create Vitest config:** `frontend/vitest.config.ts`
   ```typescript
   import { defineConfig } from 'vitest/config';
   import react from '@vitejs/plugin-react';
   
   export default defineConfig({
     plugins: [react()],
     test: {
       globals: true,
       environment: 'jsdom',
       setupFiles: './src/test/setup.ts',
     },
   });
   ```

3. **Create test setup:** `frontend/src/test/setup.ts`
   ```typescript
   import '@testing-library/jest-dom';
   ```

4. **Add test script to package.json:**
   ```json
   {
     "scripts": {
       "test": "vitest",
       "test:ui": "vitest --ui",
       "test:coverage": "vitest --coverage"
     }
   }
   ```

**Test Cases:**

**TC-1: Render Drop Zone**
```typescript
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ContractUpload } from '../ContractUpload';

describe('ContractUpload - Render', () => {
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
```

**TC-2: File Type Validation - Valid Files**
```typescript
it('should accept PDF files', async () => {
  const { user } = setup();
  const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  expect(screen.queryByText(/only pdf and docx/i)).not.toBeInTheDocument();
});

it('should accept DOCX files', async () => {
  const { user } = setup();
  const file = new File(['content'], 'contract.docx', {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  expect(screen.queryByText(/only pdf and docx/i)).not.toBeInTheDocument();
});
```

**TC-3: File Type Validation - Invalid Files**
```typescript
it('should reject TXT files with error message', async () => {
  const { user } = setup();
  const file = new File(['content'], 'document.txt', { type: 'text/plain' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  expect(screen.getByText(/only pdf and docx files are supported/i)).toBeInTheDocument();
});

it('should reject image files with error message', async () => {
  const { user } = setup();
  const file = new File(['content'], 'image.jpg', { type: 'image/jpeg' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  expect(screen.getByText(/only pdf and docx files are supported/i)).toBeInTheDocument();
});
```

**TC-4: File Size Validation - Valid Size**
```typescript
it('should accept files under 15MB', async () => {
  const { user } = setup();
  const smallFile = new File(['x'.repeat(10 * 1024 * 1024)], 'contract.pdf', {
    type: 'application/pdf'
  });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, smallFile);
  
  expect(screen.queryByText(/file size must be under 15mb/i)).not.toBeInTheDocument();
});
```

**TC-5: File Size Validation - Invalid Size**
```typescript
it('should reject files over 15MB with error message', async () => {
  const { user } = setup();
  // Create a file object with size property set
  const largeFile = new File(['content'], 'large.pdf', { type: 'application/pdf' });
  Object.defineProperty(largeFile, 'size', { value: 20 * 1024 * 1024 }); // 20MB
  
  const input = screen.getByLabelText(/upload contract/i);
  await user.upload(input, largeFile);
  
  expect(screen.getByText(/file size must be under 15mb/i)).toBeInTheDocument();
});
```

**TC-6: Upload Flow - Success**
```typescript
it('should show progress and navigate on successful upload', async () => {
  // Mock successful upload response
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      success: true,
      data: {
        contract_id: 123,  // INTEGER, not UUID
        filename: 'contract.pdf',
        size: 1024,
        upload_timestamp: '2026-08-15T10:30:00Z',
        status: 'uploaded'
      },
      error: null
    })
  });
  
  const mockNavigate = vi.fn();
  vi.mock('react-router-dom', async () => ({
    ...await vi.importActual('react-router-dom'),
    useNavigate: () => mockNavigate
  }));
  
  const { user } = setup();
  const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  // Verify upload starts
  expect(screen.getByText(/uploading/i)).toBeInTheDocument();
  
  // Wait for completion
  await waitFor(() => {
    expect(mockNavigate).toHaveBeenCalledWith('/report/123');
  });
});
```

**TC-7: Upload Flow - Network Error**
```typescript
it('should display error message and retry option on network failure', async () => {
  // Mock network error
  global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
  
  const { user } = setup();
  const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  await waitFor(() => {
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });
  
  const retryButton = screen.getByRole('button', { name: /retry/i });
  expect(retryButton).toBeInTheDocument();
  
  // Verify retry clears error
  await user.click(retryButton);
  expect(screen.queryByText(/network error/i)).not.toBeInTheDocument();
});

it('should display error message on 500 server error', async () => {
  // Mock 500 response
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 500,
    json: async () => ({
      success: false,
      data: null,
      error: 'Internal server error'
    })
  });
  
  const { user } = setup();
  const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
  const input = screen.getByLabelText(/upload contract/i);
  
  await user.upload(input, file);
  
  await waitFor(() => {
    expect(screen.getByText(/internal server error/i)).toBeInTheDocument();
  });
});
```

**TC-8: Accessibility**
```typescript
it('should be keyboard accessible', async () => {
  const { user } = setup();
  
  // Tab to drop zone
  await user.tab();
  const dropZone = screen.getByRole('button', { name: /upload contract/i });
  expect(dropZone).toHaveFocus();
  
  // Press Enter to trigger file browser
  await user.keyboard('{Enter}');
  // Note: Can't actually test file browser opening, but verify handler doesn't crash
});

it('should have proper aria labels', () => {
  render(
    <BrowserRouter>
      <ContractUpload />
    </BrowserRouter>
  );
  
  const dropZone = screen.getByLabelText(/upload contract/i);
  expect(dropZone).toBeInTheDocument();
  expect(dropZone).toHaveAttribute('aria-label');
});
```

**Test helpers:**
```typescript
function setup() {
  const user = userEvent.setup();
  const view = render(
    <BrowserRouter>
      <ContractUpload />
    </BrowserRouter>
  );
  return { user, ...view };
}
```

**Verification:**
- All tests pass: `npm run test`
- Coverage report: `npm run test:coverage`
- Expected: 100% coverage on ContractUpload component

---

## Pre-Execution Checklist

Before starting Task 1:
1. ✅ Confirm `frontend/` directory exists and is completely empty
2. ✅ Understand Stage 2 upload endpoint doesn't exist yet - tests will use mocks
3. ✅ Understand contract_id is INTEGER (number type) throughout backend
4. ✅ Have Node.js 18+ installed (check: `node --version`)
5. ✅ Have npm 9+ installed (check: `npm --version`)

**Do NOT start implementing until this tasks.md is approved.**

---

## Expected File Structure After Completion

```
frontend/
├── .env.example
├── .env.development
├── .env.production
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── public/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   ├── vite-env.d.ts
│   ├── components/
│   │   ├── ContractUpload.tsx
│   │   └── __tests__/
│   │       └── ContractUpload.test.tsx
│   ├── pages/
│   │   └── ReportPlaceholder.tsx
│   ├── types/
│   │   └── upload.types.ts
│   └── test/
│       └── setup.ts
└── node_modules/
```

---

## Notes

- **Frontend-only spec** - no backend code, Stage 2 will implement the upload endpoint
- **Tests use mocked fetch** - realistic 200/500 responses, network errors
- **contract_id always number** - matches INTEGER type from backend
- **Navigation to `/report/:contractId`** - wired up, placeholder page confirms routing works
- **Tailwind CSS** for styling - no custom CSS files beyond index.css
- **Native fetch API** - no axios dependency
- **React Router v6** - using `useNavigate` hook for programmatic navigation
- **Vitest + React Testing Library** - modern testing setup matching Vite ecosystem

---

## Dependency Versions (Approximate)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@testing-library/react": "^14.3.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0",
    "jsdom": "^24.0.0"
  }
}
```

Exact versions will be determined by Vite scaffolding and npm install at execution time.

---

## Success Criteria

After completing all tasks:

- [ ] `npm run dev` starts dev server on http://localhost:5173
- [ ] Upload page renders at `/` with drag-and-drop zone
- [ ] File type validation rejects non-PDF/DOCX with correct error
- [ ] File size validation rejects 15MB+ files with correct error
- [ ] Upload progress UI implemented (tested with mock)
- [ ] Network error handling shows error message with retry button
- [ ] Navigation to `/report/:contractId` works with numeric ID
- [ ] `npm run test` passes all tests (TC-1 through TC-8)
- [ ] Component is keyboard accessible
- [ ] No TypeScript compilation errors
- [ ] Tailwind CSS styles apply correctly
- [ ] `import.meta.env.VITE_API_BASE_URL` reads from .env files

**Stage 1 is complete when:** All success criteria met. Stage 2 (backend upload endpoint) can then wire up the real API connection.
