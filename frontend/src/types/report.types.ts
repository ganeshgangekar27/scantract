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
