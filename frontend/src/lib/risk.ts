/**
 * Risk scoring and filtering utilities for contract findings.
 */

import type { RiskSummary, RiskyClause, MissingClause, Severity } from './types';

/**
 * Finding that can be filtered by severity (risky or missing clause).
 */
type Finding = RiskyClause | MissingClause;

/**
 * Calculate risk score (0-100) from risk summary.
 * 
 * Formula:
 *   score = (high * 3 + medium * 2 + low * 1) / total_findings * 100
 * 
 * Where total_findings = high + medium + low
 * 
 * Returns 0 if there are no findings.
 * 
 * @param summary - Risk summary with severity counts
 * @returns Risk score from 0 (no risk) to 100 (all high severity)
 */
export function riskScore(summary: RiskSummary): number {
  const { high_severity_count, medium_severity_count, low_severity_count } = summary;
  
  const totalFindings = high_severity_count + medium_severity_count + low_severity_count;
  
  if (totalFindings === 0) {
    return 0;
  }
  
  const weightedSum = high_severity_count * 3 + medium_severity_count * 2 + low_severity_count * 1;
  const maxPossible = totalFindings * 3; // All findings at high severity
  
  return Math.round((weightedSum / maxPossible) * 100);
}

/**
 * Convert risk score to label.
 * 
 * - 0: 'Low'
 * - 1-50: 'Low'
 * - 51-75: 'Medium'
 * - 76-100: 'High'
 * 
 * @param score - Risk score (0-100)
 * @returns Risk level label
 */
export function riskLabel(score: number): 'Low' | 'Medium' | 'High' {
  if (score === 0 || score <= 50) {
    return 'Low';
  }
  if (score <= 75) {
    return 'Medium';
  }
  return 'High';
}

/**
 * Group findings by severity level.
 * 
 * @param findings - Array of findings (risky or missing clauses)
 * @returns Object with severity as keys and arrays of findings as values
 */
export function groupFindingsBySeverity<T extends Finding>(
  findings: T[]
): Record<Severity, T[]> {
  const groups: Record<Severity, T[]> = {
    high: [],
    medium: [],
    low: [],
  };
  
  findings.forEach((finding) => {
    groups[finding.severity].push(finding);
  });
  
  return groups;
}

/**
 * Filter findings by severity level.
 * 
 * @param findings - Array of findings (risky or missing clauses)
 * @param severity - Severity to filter by, or 'all' for no filtering
 * @returns Filtered findings
 */
export function filterBySeverity<T extends Finding>(
  findings: T[],
  severity: 'all' | Severity
): T[] {
  if (severity === 'all') {
    return findings;
  }
  return findings.filter((f) => f.severity === severity);
}

/**
 * Count findings by severity level.
 * 
 * @param findings - Array of findings (risky or missing clauses)
 * @returns Object with counts per severity level
 */
export function countBySeverity(
  findings: Finding[]
): Record<Severity, number> {
  const counts: Record<Severity, number> = {
    high: 0,
    medium: 0,
    low: 0,
  };
  
  findings.forEach((finding) => {
    counts[finding.severity]++;
  });
  
  return counts;
}

/**
 * Extract the "why it matters" text from a finding.
 * 
 * v2: Takes the LAST sentence from finding.explanation (trimmed),
 * falling back to finding.reason if explanation is empty.
 * 
 * Result is capped at 140 characters with "..." if truncated.
 * 
 * @param finding - Risky or missing clause finding
 * @returns Short explanation text, max 140 chars
 */
export function whyItMatters(finding: RiskyClause | MissingClause): string {
  const trimmedExplanation = finding.explanation.trim();
  
  let text: string;
  if (trimmedExplanation) {
    // Split on ". " and take the last non-empty sentence
    const sentences = trimmedExplanation.split('. ').filter(s => s.trim());
    if (sentences.length > 0) {
      // Get the last sentence
      const lastSentence = sentences[sentences.length - 1].trim();
      text = lastSentence;
    } else {
      text = trimmedExplanation;
    }
  } else {
    text = finding.reason.trim();
  }
  
  // Cap at 140 characters first
  if (text.length > 140) {
    return text.substring(0, 140) + '...';
  }
  
  // Add period if it doesn't end with punctuation (and we're under the cap)
  if (text && !text.match(/[.!?]$/)) {
    text = text + '.';
  }
  
  return text;
}

/**
 * Row in the top risks summary table.
 */
export interface TopRiskRow {
  key: string;       // finding_id
  label: string;     // "Clause X: ..." or expected_clause_type
  severity: Severity;
  why: string;       // from whyItMatters
}

/**
 * Get top N risks from combined risky and missing clauses.
 * 
 * Combines both lists, sorts by severity (high > medium > low),
 * preserving original order within each severity level.
 * 
 * Returns at most n rows.
 * 
 * @param riskyFindings - Risky clause findings
 * @param missingFindings - Missing clause findings
 * @param n - Maximum number of rows to return (default: 5)
 * @returns Array of top risk rows, sorted by severity
 */
export function topRisks(
  riskyFindings: RiskyClause[],
  missingFindings: MissingClause[],
  n: number = 5
): TopRiskRow[] {
  const rows: TopRiskRow[] = [];
  
  // Process risky clauses
  riskyFindings.forEach((finding) => {
    const clausePreview = finding.clause_text.substring(0, 60);
    const label = `Clause ${finding.clause_number}: ${clausePreview}${
      finding.clause_text.length > 60 ? '...' : ''
    }`;
    
    rows.push({
      key: finding.finding_id,
      label,
      severity: finding.severity,
      why: whyItMatters(finding),
    });
  });
  
  // Process missing clauses
  missingFindings.forEach((finding) => {
    rows.push({
      key: finding.finding_id,
      label: finding.expected_clause_type,
      severity: finding.severity,
      why: whyItMatters(finding),
    });
  });
  
  // Sort by severity: high first, then medium, then low
  // Within each severity, maintain original order (stable sort)
  const severityOrder: Record<Severity, number> = {
    high: 0,
    medium: 1,
    low: 2,
  };
  
  rows.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
  
  // Return at most n rows
  return rows.slice(0, n);
}
