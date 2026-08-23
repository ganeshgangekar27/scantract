# Stage 9 Frontend Tasks - Report Assembly & UI

## Context

Backend is complete and verified:
- ✅ `GET /api/contracts/{contract_id}/report` - Returns JSON report (contract_id is INTEGER)
- ✅ `GET /api/contracts/{contract_id}/report/pdf` - Returns PDF download (contract_id is INTEGER)

**CRITICAL NOTES:**

1. **contract_id is INTEGER everywhere** - TypeScript types must use `number`, not `string`, unless explicitly converting for URL construction
2. **PDF endpoint returns HTTP 500 on Windows** due to missing GTK libraries (see `backend/app/reports/README.md`) - frontend MUST handle this gracefully with clear error messaging, not crash or show blank state
3. **Backend response envelope structure:**
   ```typescript
   {
     success: boolean;
     data: ContractReport | null;
     error: string | null;
   }
   ```

## Verified Backend Response Shape

From `backend/app/reports/models.py` (exact field names):

- `contract_id`: int (not UUID)
- `filename`: str
- `upload_date`: datetime (ISO string in JSON)
- `all_clauses`: List[ClauseWithRisk]
  - `clause_id`: int
  - `clause_number`: str
  - `clause_text`: str
  - `has_risk`: bool
  - `risk_severity`: "high" | "medium" | "low" | null
  - `risk_reason`: str | null
- `risky_clauses`: List[RiskyClauseReport]
  - `finding_id`: str (UUID)
  - `clause_id`: int
  - `clause_number`: str
  - `clause_text`: str
  - `severity`: "high" | "medium" | "low"
  - `reason`: str
  - `explanation`: str
  - `formatted_citation`: str
- `missing_clauses`: List[MissingClauseReport]
  - `finding_id`: str (UUID)
  - `expected_clause_type`: str
  - `severity`: "high" | "medium" | "low"
  - `reason`: str
  - `explanation`: str
  - `formatted_citation`: str
- `risk_summary`: RiskSummary
  - `total_clauses`: int
  - `risky_clauses_count`: int
  - `missing_clauses_count`: int
  - `high_severity_count`: int
  - `medium_severity_count`: int
  - `low_severity_count`: int
  - `overall_risk_level`: "high" | "medium" | "low" | "none"
- `legal_references`: List[LegalReference]
  - `citation`: str
  - `usage_count`: int

**IMPORTANT:** Field names differ from original spec:
- ✅ `all_clauses` (not `clauses`)
- ✅ `risky_clauses_count` (not `total_risky_clauses`)
- ✅ `missing_clauses_count` (not `total_missing_clauses`)
- ✅ `upload_date` (not `upload_timestamp`)
- ✅ `has_risk` (not `is_risky`)

---

## Tasks

### Task 1: Create TypeScript Types
**File:** `frontend/src/types/report.types.ts`

Define interfaces matching EXACT backend response shape from `backend/app/reports/models.py`:

```typescript
export type Severity = 'low' | 'medium' | 'high';
export type OverallRiskLevel = 'none' | 'low' | 'medium' | 'high';

export interface ClauseWithRisk {
  clause_id: number;  // INTEGER, not string
  clause_number: string;
  clause_text: string;
  has_risk: boolean;  // NOT is_risky
  risk_severity: Severity | null;
  risk_reason: string | null;
}

export interface RiskyClauseReport {
  finding_id: string;  // UUID as string
  clause_id: number;
  clause_number: string;
  clause_text: string;
  severity: Severity;
  reason: string;
  explanation: string;
  formatted_citation: string;
}

export interface MissingClauseReport {
  finding_id: string;
  expected_clause_type: string;
  severity: Severity;
  reason: string;
  explanation: string;
  formatted_citation: string;
}

export interface RiskSummary {
  total_clauses: number;
  risky_clauses_count: number;  // NOT total_risky_clauses
  missing_clauses_count: number;  // NOT total_missing_clauses
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  overall_risk_level: OverallRiskLevel;
}

export interface LegalReference {
  citation: string;
  usage_count: number;
}

export interface ContractReport {
  contract_id: number;  // INTEGER
  filename: string;
  upload_date: string;  // ISO datetime string (NOT upload_timestamp)
  all_clauses: ClauseWithRisk[];  // NOT clauses
  risky_clauses: RiskyClauseReport[];
  missing_clauses: MissingClauseReport[];
  risk_summary: RiskSummary;
  legal_references: LegalReference[];
}

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}
```

**Verification:** Compare against `backend/app/reports/models.py` line-by-line before proceeding.

---

### Task 2: Implement useContractReport Hook
**File:** `frontend/src/hooks/useContractReport.ts`

Custom hook to fetch report data from JSON endpoint.

**Requirements:**
- Parameter: `contractId: number` (not string)
- Fetch `GET /api/contracts/${contractId}/report`
- Parse response envelope: `{ success, data, error }`
- Return: `{ report, loading, error, retry }`
- Handle 404 (contract not found / processing incomplete)
- Handle 500 (server error)
- Retry mechanism via `retry()` function

**Implementation notes:**
- Use `import.meta.env.VITE_API_BASE_URL` for base URL (defaults to empty string for dev proxy)
- Set `loading: true` during fetch
- Clear `error` state when retrying
- Use `useEffect` to fetch on mount and when `contractId` changes

---

### Task 3: Implement usePDFDownload Hook
**File:** `frontend/src/hooks/usePDFDownload.ts`

Custom hook for PDF download with EXPLICIT error handling for 500 responses.

**Requirements:**
- Parameter: `contractId: number`
- Fetch `GET /api/contracts/${contractId}/report/pdf`
- Return: `{ downloadPDF, downloading, error }`
- **MUST handle HTTP 500 gracefully** - set error state with user-friendly message: "PDF generation is currently unavailable. Please try again later or contact support."
- Do NOT throw unhandled promise rejections
- Create blob URL and trigger download on success
- Clean up blob URL after download

**Error handling flow:**
```typescript
if (!response.ok) {
  if (response.status === 500) {
    setError('PDF generation is currently unavailable. Please try again later or contact support.');
  } else if (response.status === 404) {
    setError('Contract not found.');
  } else {
    setError('Failed to download PDF.');
  }
  return;
}
```

**Download flow:**
```typescript
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `contract_${contractId}_report.pdf`;
document.body.appendChild(a);
a.click();
window.URL.revokeObjectURL(url);
document.body.removeChild(a);
```

---

### Task 4: Implement RiskSummaryHeader Component
**File:** `frontend/src/components/RiskSummaryHeader.tsx`

Sticky header displaying contract summary and PDF download button.

**Props:**
```typescript
interface RiskSummaryHeaderProps {
  filename: string;
  summary: RiskSummary;
  onDownloadPDF: () => void;
  downloading: boolean;
  downloadError: string | null;
}
```

**Requirements:**
- Sticky position at top of viewport
- Display filename prominently
- Show overall risk level with colored badge (red/yellow/blue/green)
- Display severity counts with icons/colors:
  - High: red text/background
  - Medium: yellow text/background
  - Low: blue text/background
- Download PDF button:
  - Disabled when `downloading === true`
  - Show spinner when downloading
  - **Show error toast/alert when `downloadError` is not null** (NOT silent failure)
- Responsive layout (grid on desktop, stacked on mobile)

**Error display requirement:**
When `downloadError` is present, render an error alert above or near the download button:
```tsx
{downloadError && (
  <div className="alert alert-error" role="alert">
    {downloadError}
  </div>
)}
```

---

### Task 5: Implement ContractText and ClauseHighlight Components

**File 1:** `frontend/src/components/ContractText.tsx`

Container component rendering all clauses with highlights.

**Props:**
```typescript
interface ContractTextProps {
  clauses: ClauseWithRisk[];
  onClauseClick: (clauseId: number) => void;  // number, not string
}
```

**Requirements:**
- Render clauses in order
- Pass each clause to `<ClauseHighlight />` component
- Handle click events and bubble up `onClauseClick(clause.clause_id)`

---

**File 2:** `frontend/src/components/ClauseHighlight.tsx`

Individual clause renderer with conditional highlighting.

**Props:**
```typescript
interface ClauseHighlightProps {
  clause: ClauseWithRisk;
  onClick: (clauseId: number) => void;
}
```

**Requirements:**
- Render clause number and text
- Apply background color based on `has_risk` and `risk_severity`:
  - `has_risk === false`: no highlight (white background)
  - `severity === 'high'`: red background (#FEE2E2 or similar)
  - `severity === 'medium'`: yellow background (#FEF3C7)
  - `severity === 'low'`: blue background (#DBEAFE)
- Clickable only if `has_risk === true`
- Show pointer cursor on hover for risky clauses
- Add subtle border/padding for visual separation

**Color mapping helper:**
```typescript
const getSeverityColor = (hasRisk: boolean, severity: Severity | null): string => {
  if (!hasRisk) return 'bg-white';
  switch (severity) {
    case 'high': return 'bg-red-100';
    case 'medium': return 'bg-yellow-100';
    case 'low': return 'bg-blue-100';
    default: return 'bg-white';
  }
};
```

---

### Task 6: Implement ExplanationPanel Component
**File:** `frontend/src/components/ExplanationPanel.tsx`

Side panel showing detailed explanation for selected risky clause.

**Props:**
```typescript
interface ExplanationPanelProps {
  clause: RiskyClauseReport | null;
  onClose: () => void;
}
```

**Requirements:**
- Render only when `clause !== null`
- Slide-in animation from right side
- Fixed position overlay (z-index above content)
- Close button (X icon) in top-right corner
- Click outside panel to close (overlay click handler)
- Display:
  - Clause number header
  - Severity badge (colored)
  - Clause text (quoted/italicized)
  - Reason (bold label)
  - Explanation (main content, preserve line breaks)
  - Formatted citation (monospace font, light background)
- Responsive: full-width on mobile, 40% width on desktop

**Animation:**
Use CSS transitions for smooth slide-in:
```css
.explanation-panel {
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out;
}
.explanation-panel.open {
  transform: translateX(0);
}
```

---

### Task 7: Implement MissingClausesPanel Component
**File:** `frontend/src/components/MissingClausesPanel.tsx`

Section displaying missing clause findings.

**Props:**
```typescript
interface MissingClausesPanelProps {
  missingClauses: MissingClauseReport[];
}
```

**Requirements:**
- If `missingClauses.length === 0`, show positive message:
  ```tsx
  <div className="alert alert-success">
    ✓ No missing clauses detected. All expected clauses are present.
  </div>
  ```
- Otherwise, render card-based list:
  - Each card shows:
    - Expected clause type (header)
    - Severity badge
    - Reason (why expected)
    - Explanation
    - Formatted citation (small text, gray)
  - Cards ordered by severity (high → medium → low)
  - Severity-colored left border (red/yellow/blue)
- Collapsible/expandable cards (optional, nice-to-have)

---

### Task 8: Implement ReportView Page Component
**File:** `frontend/src/pages/ReportView.tsx`

Main page component composing all report UI elements.

**Requirements:**
- Use `useParams<{ contractId: string }>()` to get route param
- **Parse contractId as number:** `const contractId = Number(params.contractId)`
- Use `useContractReport(contractId)` hook
- Use `usePDFDownload(contractId)` hook
- Manage `selectedClause` state for explanation panel
- Handle loading state: show skeleton loaders
- Handle error state: show error message with retry button
- Render when data loaded:
  ```tsx
  <RiskSummaryHeader
    filename={report.filename}
    summary={report.risk_summary}
    onDownloadPDF={downloadPDF}
    downloading={downloading}
    downloadError={downloadError}
  />
  <ContractText
    clauses={report.all_clauses}
    onClauseClick={handleClauseClick}
  />
  <MissingClausesPanel
    missingClauses={report.missing_clauses}
  />
  {selectedClause && (
    <ExplanationPanel
      clause={selectedClause}
      onClose={() => setSelectedClause(null)}
    />
  )}
  ```
- Layout: two-column on desktop (contract text + missing clauses sidebar), stacked on mobile

**Click handler:**
```typescript
const handleClauseClick = (clauseId: number) => {
  const risky = report.risky_clauses.find(c => c.clause_id === clauseId);
  if (risky) setSelectedClause(risky);
};
```

---

### Task 9: Add Report Route to Router
**File:** `frontend/src/App.tsx` (or router config file)

Add route for report view page.

**Requirements:**
- Route path: `/report/:contractId`
- Component: `<ReportView />`
- Ensure `contractId` param is available to component
- Verify router setup (React Router v6 syntax):
  ```tsx
  <Route path="/report/:contractId" element={<ReportView />} />
  ```

**Verification:**
- Navigate to `/report/1` (or any valid contract ID)
- Page should load and fetch report data
- URL param correctly parsed as number

---

### Task 10: Write Component Tests
**Directory:** `frontend/src/components/__tests__/`

Write unit tests using React Testing Library and Vitest (or Jest).

**Test Files:**

1. **`RiskSummaryHeader.test.tsx`**
   - TC-1: Renders filename and risk counts correctly
   - TC-2: PDF button shows spinner when downloading
   - TC-3: PDF button shows error alert when downloadError is not null (mock 500 scenario)
   - TC-4: PDF button calls onDownloadPDF when clicked

2. **`ClauseHighlight.test.tsx`**
   - TC-5: Applies correct background color for high severity
   - TC-6: Applies correct background color for medium severity
   - TC-7: Applies correct background color for low severity
   - TC-8: No highlight when has_risk is false
   - TC-9: onClick handler fires with correct clause_id

3. **`ExplanationPanel.test.tsx`**
   - TC-10: Renders when clause prop is provided
   - TC-11: Does not render when clause is null
   - TC-12: Calls onClose when close button clicked
   - TC-13: Displays clause details correctly (number, severity, explanation, citation)

4. **`MissingClausesPanel.test.tsx`**
   - TC-14: Shows positive message when missingClauses array is empty
   - TC-15: Renders list of missing clause cards when array has items
   - TC-16: Displays severity badges correctly

**Mock setup for fetch calls:**
```typescript
global.fetch = vi.fn();

// Mock successful report response
(fetch as Mock).mockResolvedValue({
  ok: true,
  json: async () => ({
    success: true,
    data: mockReportData,
    error: null
  })
});

// Mock 500 PDF error response
(fetch as Mock).mockResolvedValue({
  ok: false,
  status: 500,
  statusText: 'Internal Server Error'
});
```

**Required test coverage:**
- All components render without errors
- Correct props passed down
- Click handlers fire correctly
- Error states display properly (especially PDF 500 handling)
- Loading states show spinners
- Conditional rendering based on data presence

---

## Pre-Execution Checklist

Before starting Task 1:
1. ✅ Verify `backend/app/reports/models.py` field names match tasks.md types
2. ✅ Confirm `contract_id` is INTEGER (number type) in all interfaces
3. ✅ Understand PDF endpoint may return 500 on Windows dev machines
4. ✅ Confirm frontend tech stack: React + Vite + TypeScript + Tailwind CSS
5. ✅ Verify API base URL configuration (VITE_API_BASE_URL env var)

**Do NOT start implementing until this tasks.md is approved.**

---

## Expected File Structure After Completion

```
frontend/src/
├── types/
│   └── report.types.ts
├── hooks/
│   ├── useContractReport.ts
│   └── usePDFDownload.ts
├── components/
│   ├── RiskSummaryHeader.tsx
│   ├── ContractText.tsx
│   ├── ClauseHighlight.tsx
│   ├── ExplanationPanel.tsx
│   ├── MissingClausesPanel.tsx
│   └── __tests__/
│       ├── RiskSummaryHeader.test.tsx
│       ├── ClauseHighlight.test.tsx
│       ├── ExplanationPanel.test.tsx
│       └── MissingClausesPanel.test.tsx
├── pages/
│   └── ReportView.tsx
└── App.tsx (modified)
```

---

## Notes

- All `contract_id` / `contractId` references MUST be typed as `number`, never `string` (unless explicitly converting for URL construction)
- Field names MUST match backend exactly: `all_clauses`, `risky_clauses_count`, `missing_clauses_count`, `upload_date`, `has_risk`
- PDF download MUST handle 500 errors gracefully with clear user messaging
- Tests MUST include realistic 500 error scenario for PDF endpoint
- Follow React + Vite + TypeScript + Tailwind CSS conventions throughout
