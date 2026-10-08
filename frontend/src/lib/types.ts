/**
 * TypeScript types matching backend API response models.
 * 
 * NOTE: The same clause_id can appear in multiple findings with different severity.
 * Use finding_id (UUID string) as the stable unique key for each finding.
 */

/**
 * Risk severity level
 */
export type Severity = 'high' | 'medium' | 'low';

/**
 * Contract processing status
 */
export type ProcessingStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

/**
 * Overall risk level assessment
 */
export type OverallRiskLevel = 'high' | 'medium' | 'low' | 'none';

/**
 * Risky clause finding from report.
 * 
 * Includes the clause details, risk assessment, and cached explanation/citation.
 * finding_id is a UUID string and serves as the unique key for this finding.
 */
export interface RiskyClause {
  finding_id: string;  // UUID as string - unique key for this finding
  clause_id: number;   // INTEGER - same clause_id can have multiple findings
  clause_number: string;
  clause_text: string;
  severity: Severity;
  reason: string;
  explanation: string;
  formatted_citation: string;
}

/**
 * Missing clause finding from report.
 * 
 * Identifies expected clauses that are absent from the contract.
 * finding_id is a UUID string and serves as the unique key for this finding.
 */
export interface MissingClause {
  finding_id: string;  // UUID as string - unique key for this finding
  expected_clause_type: string;
  severity: Severity;
  reason: string;
  explanation: string;
  formatted_citation: string;
}

/**
 * Aggregate risk statistics for a contract.
 */
export interface RiskSummary {
  total_clauses: number;
  risky_clauses_count: number;
  missing_clauses_count: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  overall_risk_level: OverallRiskLevel;
}

/**
 * Clause annotated with risk information.
 */
export interface ClauseWithRisk {
  clause_id: number;
  clause_number: string;
  clause_text: string;
  has_risk: boolean;
  risk_severity: Severity | null;
  risk_reason: string | null;
}

/**
 * Legal citation with usage tracking.
 */
export interface LegalReference {
  citation: string;
  usage_count: number;
}

/**
 * Complete contract risk report.
 * 
 * Note: Backend wraps this in {success, data, error} envelope.
 * The apiRequest function in api.ts unwraps it automatically.
 */
export interface Report {
  contract_id: number;
  filename: string;
  upload_date: string;  // ISO datetime string
  all_clauses: ClauseWithRisk[];
  risky_clauses: RiskyClause[];
  missing_clauses: MissingClause[];
  risk_summary: RiskSummary;
  legal_references: LegalReference[];
}

/**
 * Contract list item from /api/contracts/list endpoint.
 */
export interface ContractListItem {
  contract_id: number;
  filename: string;
  uploaded_at: string;  // ISO datetime string
  processing_status: ProcessingStatus;
  pipeline_stage: string | null;
  failed_stage: string | null;
  error_message: string | null;
  is_sample: boolean;
}

/**
 * Response from contract upload endpoint.
 */
export interface UploadResponse {
  contract_id: number;
  filename: string;
  size: number;  // bytes
  upload_timestamp: string;  // ISO datetime string
  status: ProcessingStatus;
}

/**
 * Pipeline status response (from pipeline trigger endpoints).
 */
export interface PipelineStatus {
  success: boolean;
  contract_id: number;
  pipeline_stage: string;
  processing_status: ProcessingStatus;
  message: string;
  details?: Record<string, unknown> | null;
  error?: string | null;
}
