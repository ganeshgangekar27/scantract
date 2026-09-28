# Stage 9: Report Assembly & UI (Frontend) - Tasks

**Spec:** Frontend report display for contract risk analysis  
**Dependencies:** Backend Stage 9 complete (GET /api/contracts/{id}/report endpoints verified)  
**Status:** Ready to execute

---

## Context & Critical Notes

**Backend Status (Verified):**
- ✅ GET `/api/contracts/{contractId}/report` - Returns JSON report
- ✅ GET `/api/contracts/{contractId}/report/pdf` - Returns PDF (500 on Windows dev, works in Docker)
- ✅ `contract_id` is `INTEGER` throughout (not UUID)
- ✅ Real contracts exist in database (e.g., contract_id=3 from Stage 2 smoke test)

**Frontend Status (Existing):**
- ✅ Vite + React + TypeScript + Tailwind CSS configured
- ✅ react-router-dom setup in `frontend/src/App.tsx`
- ✅ Route `/report/:contractId` exists (currently renders `ReportPlaceholder.tsx`)
- ✅ Stage 1 upload UI complete (`ContractUpload.tsx`)

**Critical Requirements:**
1. `contractId` must be typed as `number` in TypeScript (not string), parse from URL params
2. PDF download MUST handle 500 errors gracefully (clear error message, not crash)
3. TypeScript types MUST match actual backend response shape (see `backend/app/reports/models.py`)
4. Replace existing `ReportPlaceholder.tsx` route, don't create competing routing

---

## Task 1: Create TypeScript Report Types

**Goal:** Define TypeScript interfaces matching the REAL backend response shape.

**File to create:** `frontend/src/types/report.types.ts`

**Source of truth:** `backend/app/reports/models.py` (verified above)

**Interfaces to define:**

```typescript
export interface ClauseWithRisk {
  clause_id: number;  // INTEGER, not UUID
  clause_number: string;  // e.g., "1.", "2.", "3."
  clause_text: string;
  has_risk: boolean;
  risk_severity: 'high' | 'medium' | 'low' | null;  // null if no risk
  risk_reason: string | null;
}

export interface RiskyClauseReport {
  finding_id: string;  // UUID as string
  clause_id: number;  // INTEGER
  clause_number: string;
  clause_text: string;
  severity: 'high' | 'medium' | 'low';
  reason: string;
  explanation: string;  // From Stage 8 cached value
  formatted_citation: string;  // From Stage 8 cached value
}

export interface MissingClauseReport {
  finding_id: string;  // UUID as string
  expected_clause_type: string;
  severity: 'high' | 'medium' | 'low';
  reason: string;
  explanation: string;  // From Stage 8 cached value
  formatted_citation: string;  // From Stage 8 cached value
}

export interface RiskSummary {
  total_clauses: number;
  risky_clauses_count: number;
  missing_clauses_count: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  overall_risk_level: 'high' | 'medium' | 'low' | 'none';
}

export interface LegalReference {
  citation: string;  // Formatted citation from Stage 8
  usage_count: number;
}

export interface ContractReport {
  contract_id: number;  // INTEGER
  filename: string;
  upload_date: string;  // ISO datetime string from backend
  all_clauses: ClauseWithRisk[];
  risky_clauses: RiskyClauseReport[];
  missing_clauses: MissingClauseReport[];
  risk_summary: RiskSummary;
  legal_references: LegalReference[];
}
```

**Acceptance Criteria:**
- All field names match backend exactly (snake_case, not camelCase)
- `contract_id` and `clause_id` typed as `number`, not `string`
- Severity types use strict literal unions
- No optional fields that backend returns as required

---

## Task 2: Implement Contract Report Hook

**Goal:** Fetch contract report JSON from backend with proper loading/error states.

**File to create:** `frontend/src/hooks/useContractReport.ts`

**Implementation:**

```typescript
import { useState, useEffect } from 'react';
import { ContractReport } from '../types/report.types';

interface UseContractReportResult {
  report: ContractReport | null;
  loading: boolean;
  error: string | null;
}

export function useContractReport(contractId: number): UseContractReportResult {
  const [report, setReport] = useState<ContractReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`/api/contracts/${contractId}/report`);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Contract not found');
          }
          throw new Error(`Failed to load report: ${response.statusText}`);
        }
        
        const data = await response.json();
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [contractId]);

  return { report, loading, error };
}
```

**Key requirements:**
- `contractId` parameter typed as `number`
- Handle 404 specifically (contract not found)
- Handle non-200 responses with clear error messages
- Re-fetch if `contractId` changes

**Acceptance Criteria:**
- Hook returns `{ report, loading, error }`
- `contractId` typed as `number`
- Error messages are user-friendly
- Loading state manages properly during fetch

---

## Task 3: Implement PDF Download Hook

**Goal:** Handle PDF download with explicit 500 error handling for Windows dev environments.

**File to create:** `frontend/src/hooks/usePDFDownload.ts`

**Implementation:**

```typescript
import { useState } from 'react';

interface UsePDFDownloadResult {
  downloadPDF: () => Promise<void>;
  downloading: boolean;
  error: string | null;
}

export function usePDFDownload(contractId: number, filename: string): UsePDFDownloadResult {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const downloadPDF = async () => {
    try {
      setDownloading(true);
      setError(null);
      
      const response = await fetch(`/api/contracts/${contractId}/report/pdf`);
      
      if (!response.ok) {
        // CRITICAL: Handle 500 gracefully for Windows dev environments
        if (response.status === 500) {
          throw new Error('PDF generation is currently unavailable. This feature requires Docker deployment.');
        }
        throw new Error(`Failed to download PDF: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}_report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      throw err; // Re-throw so caller can handle if needed
    } finally {
      setDownloading(false);
    }
  };

  return { downloadPDF, downloading, error };
}
```

**Key requirements:**
- MUST handle 500 errors with clear message about Docker requirement
- Use browser download mechanism (blob + temporary anchor)
- Clean up blob URLs after download
- Re-throw errors so component can show toast/alert

**Acceptance Criteria:**
- 500 errors show clear message (not crash or blank state)
- Successful downloads trigger browser save dialog
- Error state exposed to component for UI feedback
- Blob URLs cleaned up properly

---

## Task 4: Implement Risk Summary Header

**Goal:** Display contract metadata, overall risk level, and PDF download button with error handling.

**File to create:** `frontend/src/components/RiskSummaryHeader.tsx`

**Component structure:**
- Contract filename and upload date
- Overall risk level badge (color-coded: red=high, yellow=medium, blue=low, green=none)
- Severity counts (high/medium/low findings)
- Download PDF button with loading/error states

**Error handling:**
- If PDF download fails, show error toast/alert with message from `usePDFDownload.error`
- Don't silence 500 errors - make them visible to user

**Styling:**
- Use Tailwind CSS
- Badge colors: `bg-red-100 text-red-800` (high), `bg-yellow-100 text-yellow-800` (medium), `bg-blue-100 text-blue-800` (low), `bg-green-100 text-green-800` (none)
- Button disabled state while downloading

**Acceptance Criteria:**
- Displays all risk summary data
- PDF button shows loading spinner while downloading
- PDF errors display in clear alert/toast (not console-only)
- Risk level badge color-coded correctly
- Responsive layout

---

## Task 5: Implement Contract Text & Clause Highlighting

**Goal:** Render all contract clauses with severity-based highlighting and click handlers.

**Files to create:**
- `frontend/src/components/ContractText.tsx` - Container for all clauses
- `frontend/src/components/ClauseHighlight.tsx` - Individual clause with highlighting

**ContractText props:**
```typescript
interface ContractTextProps {
  clauses: ClauseWithRisk[];
  selectedClauseId: number | null;
  onClauseClick: (clauseId: number) => void;
}
```

**ClauseHighlight props:**
```typescript
interface ClauseHighlightProps {
  clause: ClauseWithRisk;
  isSelected: boolean;
  onClick: () => void;
}
```

**Highlighting logic:**
- `has_risk === false`: No background (white/default)
- `risk_severity === 'high'`: `bg-red-50 hover:bg-red-100 border-l-4 border-red-500`
- `risk_severity === 'medium'`: `bg-yellow-50 hover:bg-yellow-100 border-l-4 border-yellow-500`
- `risk_severity === 'low'`: `bg-blue-50 hover:bg-blue-100 border-l-4 border-blue-500`
- Selected clause: Add `ring-2 ring-blue-500` border

**Acceptance Criteria:**
- All clauses rendered in order (by `clause_number`)
- Correct background color per severity
- Click handler fires with `clause_id` (number)
- Selected state visually distinct
- Cursor pointer on risky clauses only

---

## Task 6: Implement Explanation Panel

**Goal:** Side panel showing selected risky clause details with explanation and citation.

**File to create:** `frontend/src/components/ExplanationPanel.tsx`

**Props:**
```typescript
interface ExplanationPanelProps {
  clause: RiskyClauseReport | null;  // null = panel closed
  onClose: () => void;
}
```

**Content:**
- Clause number badge
- Severity badge (high/medium/low with color)
- Clause text (quoted/indented)
- "Why this is risky" section with `reason`
- "Detailed explanation" section with `explanation`
- "Legal reference" section with `formatted_citation`
- Close button (X icon)

**Layout:**
- Fixed position on right side of screen
- Slide-in animation when opening
- Overlay/backdrop on mobile (optional)
- Scrollable content area

**Acceptance Criteria:**
- Opens when clause selected (clause !== null)
- Closes on X button click
- Shows all clause details correctly
- Severity badge matches severity value
- Citation displayed as formatted text (not raw)
- Responsive (full-width on mobile, sidebar on desktop)

---

## Task 7: Implement Missing Clauses Panel

**Goal:** Display list of missing clauses with positive message if empty.

**File to create:** `frontend/src/components/MissingClausesPanel.tsx`

**Props:**
```typescript
interface MissingClausesPanelProps {
  missingClauses: MissingClauseReport[];
}
```

**Content:**
- Title: "Missing Clauses"
- If empty: Positive message "✓ No required clauses are missing from this contract"
- If not empty: List of missing clause cards with:
  - Expected clause type (e.g., "Termination Notice Clause")
  - Severity badge
  - Reason
  - Explanation (expandable/collapsible)
  - Citation

**Styling:**
- Use Tailwind card layout
- Severity badges same as risky clauses
- Empty state: `bg-green-50 border-green-200` with checkmark icon

**Acceptance Criteria:**
- Shows positive message when list is empty
- Renders all missing clauses when present
- Severity badges color-coded correctly
- Citations displayed formatted
- Responsive layout

---

## Task 8: Implement Report View Page

**Goal:** Compose all components into complete report view with state management.

**File to create:** `frontend/src/pages/ReportView.tsx`

**Implementation:**
```typescript
import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { useContractReport } from '../hooks/useContractReport';
import { RiskSummaryHeader } from '../components/RiskSummaryHeader';
import { ContractText } from '../components/ContractText';
import { ExplanationPanel } from '../components/ExplanationPanel';
import { MissingClausesPanel } from '../components/MissingClausesPanel';

export function ReportView() {
  const { contractId } = useParams<{ contractId: string }>();
  const contractIdNum = parseInt(contractId || '0', 10);
  
  const { report, loading, error } = useContractReport(contractIdNum);
  const [selectedClauseId, setSelectedClauseId] = useState<number | null>(null);
  
  // Find selected clause in risky_clauses
  const selectedClause = selectedClauseId
    ? report?.risky_clauses.find(c => c.clause_id === selectedClauseId) || null
    : null;
  
  // Loading state
  if (loading) {
    return <div>Loading report...</div>;
  }
  
  // Error state
  if (error) {
    return <div>Error: {error}</div>;
  }
  
  // No report (shouldn't happen if no error)
  if (!report) {
    return <div>Report not found</div>;
  }
  
  return (
    <div className="report-view">
      <RiskSummaryHeader 
        report={report} 
        contractId={contractIdNum}
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-2">
          <ContractText
            clauses={report.all_clauses}
            selectedClauseId={selectedClauseId}
            onClauseClick={setSelectedClauseId}
          />
        </div>
        
        <div>
          <MissingClausesPanel missingClauses={report.missing_clauses} />
        </div>
      </div>
      
      <ExplanationPanel
        clause={selectedClause}
        onClose={() => setSelectedClauseId(null)}
      />
    </div>
  );
}
```

**Key requirements:**
- Parse `contractId` from URL params as number (not string)
- Handle loading state (spinner/skeleton)
- Handle error state (clear error message)
- Manage `selectedClauseId` state for explanation panel
- Layout: 2-column grid (contract text + missing clauses)
- Explanation panel overlays/slides in when clause selected

**Acceptance Criteria:**
- `contractId` parsed to number before use
- Loading state shows spinner/message
- Error state shows error message
- Selected clause state wired correctly
- All components composed properly
- Responsive layout

---

## Task 9: Replace Placeholder Route

**Goal:** Wire ReportView into existing router, remove placeholder.

**File to modify:** `frontend/src/App.tsx`

**Changes:**
1. Import `ReportView` instead of `ReportPlaceholder`
2. Replace route: `<Route path="/report/:contractId" element={<ReportView />} />`
3. Verify `contractId` param handling (parsed as number in ReportView)

**File to remove/archive:** `frontend/src/pages/ReportPlaceholder.tsx`

**Acceptance Criteria:**
- `/report/:contractId` route renders `ReportView`
- `ReportPlaceholder.tsx` deleted or moved to archive
- Navigation from upload page to report works
- Direct URL access to `/report/3` works (uses real contract)

---

## Task 10: Write Component Tests

**Goal:** Test all new components with React Testing Library.

**Files to create:**
- `frontend/src/components/__tests__/RiskSummaryHeader.test.tsx`
- `frontend/src/components/__tests__/ClauseHighlight.test.tsx`
- `frontend/src/components/__tests__/ExplanationPanel.test.tsx`
- `frontend/src/components/__tests__/MissingClausesPanel.test.tsx`

**Test scenarios:**

### RiskSummaryHeader.test.tsx
- Renders contract metadata correctly
- Shows correct risk level badge color
- PDF button shows loading state while downloading
- PDF button shows error alert when download fails (mock 500 response)
- Severity counts display correctly

### ClauseHighlight.test.tsx
- Renders clause text
- Applies correct background color for high/medium/low severity
- No background for clauses without risk
- Click handler fires with correct clause_id
- Selected state shows ring border

### ExplanationPanel.test.tsx
- Renders when clause provided
- Shows severity badge with correct color
- Displays explanation and citation
- Close button fires onClose handler
- Doesn't render when clause is null

### MissingClausesPanel.test.tsx
- Shows positive message when list is empty
- Renders list of missing clauses when present
- Each clause shows severity badge
- Citation displayed correctly

**Mock setup:**
- Mock `fetch` calls for hook tests
- Mock both success (200) and failure (500, 404) responses
- Use `@testing-library/react` for rendering
- Use `@testing-library/user-event` for interactions

**Acceptance Criteria:**
- All tests pass: `npm run test`
- Coverage for success and error scenarios
- PDF 500 error scenario explicitly tested
- No console errors during test runs

---

## Task 11: Manual Verification with Real Data

**Goal:** Verify report display with real contract from Stage 2 smoke test.

**Prerequisites:**
- Backend server running: `uvicorn app.main:app --reload` (from `backend/`)
- Frontend dev server running: `npm run dev` (from `frontend/`)
- Real contract exists: contract_id=3 (verified in Stage 2 end-to-end test)

**Verification steps:**
1. Navigate to `http://localhost:5173/report/3`
2. Verify report loads (contract filename: "test_contract.pdf")
3. Verify 4 clauses render with correct text
4. Check clause highlighting (if risk findings exist for this contract)
5. Click a risky clause → explanation panel opens
6. Check missing clauses section
7. Click PDF download button → verify 500 error shows clear message (not crash)
8. Check browser console for errors (should be none except expected 500)

**Expected behavior:**
- Report loads without errors
- All sections render correctly
- PDF button shows clear error (Windows dev environment limitation)
- No unhandled promise rejections
- No React warnings in console

**Acceptance Criteria:**
- Real contract data displays correctly
- PDF error handled gracefully
- No console errors (except expected 500 warning)
- All interactions work (click clause, close panel, etc.)

---

## Summary

**Total Tasks:** 11 (10 implementation + 1 manual verification)

**Critical Success Criteria:**
1. ✅ `contractId` typed as `number` throughout
2. ✅ PDF 500 errors handled gracefully with clear message
3. ✅ TypeScript types match actual backend response shape
4. ✅ Existing `ReportPlaceholder` route replaced (not duplicated)
5. ✅ All components tested with realistic success/error scenarios

**Files to Create (15 new files):**
- `frontend/src/types/report.types.ts`
- `frontend/src/hooks/useContractReport.ts`
- `frontend/src/hooks/usePDFDownload.ts`
- `frontend/src/components/RiskSummaryHeader.tsx`
- `frontend/src/components/ContractText.tsx`
- `frontend/src/components/ClauseHighlight.tsx`
- `frontend/src/components/ExplanationPanel.tsx`
- `frontend/src/components/MissingClausesPanel.tsx`
- `frontend/src/pages/ReportView.tsx`
- `frontend/src/components/__tests__/RiskSummaryHeader.test.tsx`
- `frontend/src/components/__tests__/ClauseHighlight.test.tsx`
- `frontend/src/components/__tests__/ExplanationPanel.test.tsx`
- `frontend/src/components/__tests__/MissingClausesPanel.test.tsx`

**Files to Modify (1 file):**
- `frontend/src/App.tsx` (replace placeholder route)

**Files to Remove (1 file):**
- `frontend/src/pages/ReportPlaceholder.tsx` (replaced by ReportView)

**Expected Test Results:**
- All component tests pass
- Manual verification with contract_id=3 successful
- PDF error handling verified (500 → clear message, not crash)

**Next Stage Dependencies:**
- Stage 10 (Docker deployment) will fix PDF generation 500 errors
- This frontend will work without changes once backend deploys to Docker
