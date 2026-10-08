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
