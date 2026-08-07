# Spec: Contract Upload Page

## Overview
Build the frontend contract upload page for ScanTract — the entry point where users drag-and-drop or browse to upload rental/freelance contracts for analysis. This corresponds to Stage 1 (Contract Upload) in the ScanTract pipeline.

## Scope
- Single-page React component with TypeScript + Tailwind CSS
- Drag-and-drop + click-to-browse file input
- Client-side validation (file type, size)
- Upload progress tracking
- POST to backend `/api/contracts/upload` endpoint
- Navigation to results page after successful upload

## Requirements

### Functional Requirements

**FR-1: File Input Interface**
- Provide a drag-and-drop zone with clear visual feedback (hover state, active drop state)
- Provide a "Browse Files" button as an alternative to drag-and-drop
- Display clear instructions: "Drag and drop your contract here or click to browse"

**FR-2: File Type Validation**
- Accept only `.pdf` and `.docx` files
- Reject other file types immediately with inline error message
- Error message: "Only PDF and DOCX files are supported"

**FR-3: File Size Validation**
- Maximum file size: 15MB
- Reject files exceeding limit with inline error message
- Error message: "File size must be under 15MB"

**FR-4: Upload Progress**
- Show upload progress bar during file transfer (0-100%)
- Display "Uploading..." state with percentage
- After upload completes, show "Processing..." state

**FR-5: Backend Integration**
- POST file as `multipart/form-data` to `/api/contracts/upload`
- Use environment variable `VITE_API_BASE_URL` for backend URL (no hardcoding)
- Handle network errors gracefully with user-friendly error messages

**FR-6: Navigation**
- On successful upload response, navigate to results page
- Pass contract ID from backend response to results page route
- Results page should show loading skeleton while backend processes stages 2-9

### Non-Functional Requirements

**NFR-1: Reusability**
- Component must be self-contained and reusable
- Backend URL configurable via environment variable
- No hardcoded URLs or API endpoints

**NFR-2: Accessibility**
- Keyboard accessible (file input via Enter/Space on button)
- Screen reader friendly (aria-labels on interactive elements)
- Focus states clearly visible

**NFR-3: Error Handling**
- All validation errors shown inline, not as alerts
- Network errors shown with retry option
- Errors must never log contract content in plaintext (security requirement)

**NFR-4: Testing**
- Unit tests with React Testing Library
- Test file validation (type, size)
- Test upload flow (mock API calls)
- Test error states

## Technical Design

### Component Structure

**Location:** `frontend/src/components/ContractUpload.tsx`

**Key State:**
```typescript
interface UploadState {
  file: File | null;
  uploading: boolean;
  uploadProgress: number;
  processing: boolean;
  error: string | null;
}
```

**Props:**
```typescript
interface ContractUploadProps {
  onUploadComplete?: (contractId: string) => void; // Optional callback
}
```

### API Contract

**Endpoint:** `POST /api/contracts/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Field name: `file`
- File: Binary content

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "contract_id": "uuid-string",
    "filename": "contract.pdf",
    "size": 1234567,
    "upload_timestamp": "2026-08-06T10:30:00Z"
  },
  "error": null
}
```

**Response (Error):**
```json
{
  "success": false,
  "data": null,
  "error": "Invalid file type"
}
```

### Environment Configuration

**File:** `frontend/.env.development`
```
VITE_API_BASE_URL=http://localhost:8000
```

**File:** `frontend/.env.production`
```
VITE_API_BASE_URL=https://api.scantract.com
```

### Validation Logic

**File Type Check:**
```typescript
const ALLOWED_TYPES = ['.pdf', '.docx'];
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
];

function isValidFileType(file: File): boolean {
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  return ALLOWED_TYPES.includes(extension) && 
         ALLOWED_MIME_TYPES.includes(file.type);
}
```

**File Size Check:**
```typescript
const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB in bytes

function isValidFileSize(file: File): boolean {
  return file.size <= MAX_FILE_SIZE;
}
```

### Upload Flow

1. User drops file or selects via file browser
2. **Client-side validation:**
   - Check file type → show error if invalid
   - Check file size → show error if too large
3. If valid, set `uploading: true` and initiate POST
4. Track upload progress with `XMLHttpRequest.upload.onprogress` or `axios` onUploadProgress
5. On successful response:
   - Set `processing: true`
   - Extract `contract_id` from response
   - Navigate to `/results/:contractId`
6. On error:
   - Display error message inline
   - Allow user to retry or select different file

### Styling (Tailwind CSS)

**Drop Zone States:**
- Default: `border-2 border-dashed border-gray-300 bg-gray-50`
- Hover: `border-blue-400 bg-blue-50`
- Active (dragging over): `border-blue-600 bg-blue-100`
- Error: `border-red-400 bg-red-50`

**Upload Progress Bar:**
- Container: `w-full bg-gray-200 rounded-full h-2.5`
- Progress: `bg-blue-600 h-2.5 rounded-full transition-all duration-300`

## Test Plan

**Test File:** `frontend/src/components/__tests__/ContractUpload.test.tsx`

**Test Cases:**

1. **TC-1: Render Drop Zone**
   - Component renders with drop zone and browse button
   - Instructions text is visible

2. **TC-2: File Type Validation - Valid**
   - Upload `.pdf` file → no error
   - Upload `.docx` file → no error

3. **TC-3: File Type Validation - Invalid**
   - Upload `.txt` file → error: "Only PDF and DOCX files are supported"
   - Upload `.jpg` file → error shown

4. **TC-4: File Size Validation - Valid**
   - Upload 10MB file → no error

5. **TC-5: File Size Validation - Invalid**
   - Upload 20MB file → error: "File size must be under 15MB"

6. **TC-6: Upload Flow - Success**
   - Mock successful API response
   - Verify upload progress shown
   - Verify processing state shown
   - Verify navigation to results page

7. **TC-7: Upload Flow - Network Error**
   - Mock failed API call
   - Verify error message displayed
   - Verify retry option available

8. **TC-8: Accessibility**
   - File input is keyboard accessible
   - Aria-labels present on interactive elements

## Dependencies

**Frontend Packages (to be installed):**
```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x",
    "axios": "^1.x"
  },
  "devDependencies": {
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x",
    "@testing-library/react": "^14.x",
    "@testing-library/jest-dom": "^6.x",
    "@testing-library/user-event": "^14.x",
    "vitest": "^1.x",
    "jsdom": "^24.x"
  }
}
```

## Files to Create/Modify

### New Files
1. `frontend/src/components/ContractUpload.tsx` - Main component
2. `frontend/src/components/__tests__/ContractUpload.test.tsx` - Test suite
3. `frontend/.env.development` - Dev environment variables
4. `frontend/.env.production` - Prod environment variables (template)
5. `frontend/src/types/upload.types.ts` - TypeScript interfaces for upload

### Modified Files
1. `frontend/src/App.tsx` - Add route for upload page
2. `frontend/vite.config.ts` - Ensure env variables are loaded
3. `frontend/package.json` - Add dependencies

## Out of Scope
- Backend `/api/contracts/upload` endpoint implementation (separate spec)
- Results page implementation (separate spec)
- Document processing pipeline (stages 2-9)
- Authentication/authorization
- Multi-file upload
- Resume interrupted uploads

## Success Criteria
- [ ] Component renders with drag-and-drop zone and browse button
- [ ] File type validation rejects non-PDF/DOCX files with clear error
- [ ] File size validation rejects files over 15MB with clear error
- [ ] Upload progress bar shows during file transfer
- [ ] Processing state displays after upload completes
- [ ] Successful upload navigates to results page with contract ID
- [ ] Network errors display user-friendly messages
- [ ] Component uses `VITE_API_BASE_URL` environment variable
- [ ] All tests pass with React Testing Library
- [ ] Component is keyboard accessible
- [ ] No contract content logged in plaintext

## Notes
- This spec covers Stage 1 of the ScanTract pipeline (Contract Upload)
- The backend endpoint will be defined in a separate spec
- Results page and stages 2-9 processing will be covered in subsequent specs
- Follow Conventional Commits: use `feat:` prefix for commits related to this spec
