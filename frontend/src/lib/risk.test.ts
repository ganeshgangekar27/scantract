import { describe, it, expect } from 'vitest';
import { riskScore, riskLabel, groupFindingsBySeverity, filterBySeverity, countBySeverity } from './risk';
import type { RiskSummary, RiskyClause, MissingClause } from './types';

describe('riskScore', () => {
  it('returns 0 for empty summary', () => {
    const summary: RiskSummary = {
      total_clauses: 10,
      risky_clauses_count: 0,
      missing_clauses_count: 0,
      high_severity_count: 0,
      medium_severity_count: 0,
      low_severity_count: 0,
      overall_risk_level: 'none',
    };
    expect(riskScore(summary)).toBe(0);
  });

  it('returns 100 for all high severity findings', () => {
    const summary: RiskSummary = {
      total_clauses: 10,
      risky_clauses_count: 5,
      missing_clauses_count: 0,
      high_severity_count: 5,
      medium_severity_count: 0,
      low_severity_count: 0,
      overall_risk_level: 'high',
    };
    expect(riskScore(summary)).toBe(100);
  });

  it('calculates correct score for mixed severity', () => {
    const summary: RiskSummary = {
      total_clauses: 10,
      risky_clauses_count: 6,
      missing_clauses_count: 0,
      high_severity_count: 2,  // 2 * 3 = 6
      medium_severity_count: 2,  // 2 * 2 = 4
      low_severity_count: 2,  // 2 * 1 = 2
      overall_risk_level: 'high',
    };
    // weighted sum = 6 + 4 + 2 = 12
    // max possible = 6 * 3 = 18
    // score = 12/18 * 100 = 66.67 -> 67
    expect(riskScore(summary)).toBe(67);
  });

  it('calculates correct score for only medium severity', () => {
    const summary: RiskSummary = {
      total_clauses: 10,
      risky_clauses_count: 3,
      missing_clauses_count: 0,
      high_severity_count: 0,
      medium_severity_count: 3,
      low_severity_count: 0,
      overall_risk_level: 'medium',
    };
    // weighted sum = 3 * 2 = 6
    // max possible = 3 * 3 = 9
    // score = 6/9 * 100 = 66.67 -> 67
    expect(riskScore(summary)).toBe(67);
  });

  it('calculates correct score for only low severity', () => {
    const summary: RiskSummary = {
      total_clauses: 10,
      risky_clauses_count: 4,
      missing_clauses_count: 0,
      high_severity_count: 0,
      medium_severity_count: 0,
      low_severity_count: 4,
      overall_risk_level: 'low',
    };
    // weighted sum = 4 * 1 = 4
    // max possible = 4 * 3 = 12
    // score = 4/12 * 100 = 33.33 -> 33
    expect(riskScore(summary)).toBe(33);
  });
});

describe('riskLabel', () => {
  it('returns Low for score 0', () => {
    expect(riskLabel(0)).toBe('Low');
  });

  it('returns Low for score 1-50', () => {
    expect(riskLabel(1)).toBe('Low');
    expect(riskLabel(25)).toBe('Low');
    expect(riskLabel(50)).toBe('Low');
  });

  it('returns Medium for score 51-75', () => {
    expect(riskLabel(51)).toBe('Medium');
    expect(riskLabel(60)).toBe('Medium');
    expect(riskLabel(75)).toBe('Medium');
  });

  it('returns High for score 76-100', () => {
    expect(riskLabel(76)).toBe('High');
    expect(riskLabel(90)).toBe('High');
    expect(riskLabel(100)).toBe('High');
  });
});

describe('groupFindingsBySeverity', () => {
  it('returns empty groups for empty list', () => {
    const findings: RiskyClause[] = [];
    const groups = groupFindingsBySeverity(findings);
    expect(groups.high).toEqual([]);
    expect(groups.medium).toEqual([]);
    expect(groups.low).toEqual([]);
  });

  it('groups only high severity findings', () => {
    const findings: RiskyClause[] = [
      {
        finding_id: 'uuid-1',
        clause_id: 1,
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'high',
        reason: 'Bad',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        clause_id: 2,
        clause_number: '1.2',
        clause_text: 'Test',
        severity: 'high',
        reason: 'Bad',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const groups = groupFindingsBySeverity(findings);
    expect(groups.high).toHaveLength(2);
    expect(groups.medium).toHaveLength(0);
    expect(groups.low).toHaveLength(0);
  });

  it('groups mixed severity findings', () => {
    const findings: RiskyClause[] = [
      {
        finding_id: 'uuid-1',
        clause_id: 1,
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'high',
        reason: 'Bad',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        clause_id: 2,
        clause_number: '1.2',
        clause_text: 'Test',
        severity: 'medium',
        reason: 'Questionable',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-3',
        clause_id: 3,
        clause_number: '1.3',
        clause_text: 'Test',
        severity: 'low',
        reason: 'Minor',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const groups = groupFindingsBySeverity(findings);
    expect(groups.high).toHaveLength(1);
    expect(groups.medium).toHaveLength(1);
    expect(groups.low).toHaveLength(1);
  });

  it('handles duplicate clause_id with different severity', () => {
    const findings: RiskyClause[] = [
      {
        finding_id: 'uuid-1',
        clause_id: 1,  // Same clause_id
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'high',
        reason: 'First issue',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        clause_id: 1,  // Same clause_id, different finding
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'medium',
        reason: 'Second issue',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const groups = groupFindingsBySeverity(findings);
    expect(groups.high).toHaveLength(1);
    expect(groups.high[0].finding_id).toBe('uuid-1');
    expect(groups.medium).toHaveLength(1);
    expect(groups.medium[0].finding_id).toBe('uuid-2');
  });
});

describe('filterBySeverity', () => {
  const findings: RiskyClause[] = [
    {
      finding_id: 'uuid-1',
      clause_id: 1,
      clause_number: '1.1',
      clause_text: 'Test',
      severity: 'high',
      reason: 'Bad',
      explanation: 'Explanation',
      formatted_citation: 'Citation',
    },
    {
      finding_id: 'uuid-2',
      clause_id: 2,
      clause_number: '1.2',
      clause_text: 'Test',
      severity: 'medium',
      reason: 'Questionable',
      explanation: 'Explanation',
      formatted_citation: 'Citation',
    },
    {
      finding_id: 'uuid-3',
      clause_id: 3,
      clause_number: '1.3',
      clause_text: 'Test',
      severity: 'low',
      reason: 'Minor',
      explanation: 'Explanation',
      formatted_citation: 'Citation',
    },
  ];

  it('returns all findings for "all" filter', () => {
    const filtered = filterBySeverity(findings, 'all');
    expect(filtered).toHaveLength(3);
  });

  it('filters only high severity findings', () => {
    const filtered = filterBySeverity(findings, 'high');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].severity).toBe('high');
  });

  it('filters only medium severity findings', () => {
    const filtered = filterBySeverity(findings, 'medium');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].severity).toBe('medium');
  });

  it('filters only low severity findings', () => {
    const filtered = filterBySeverity(findings, 'low');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].severity).toBe('low');
  });

  it('returns empty array when no findings match', () => {
    const highOnly: RiskyClause[] = [findings[0]];
    const filtered = filterBySeverity(highOnly, 'low');
    expect(filtered).toHaveLength(0);
  });
});

describe('countBySeverity', () => {
  it('returns zero counts for empty list', () => {
    const counts = countBySeverity([]);
    expect(counts.high).toBe(0);
    expect(counts.medium).toBe(0);
    expect(counts.low).toBe(0);
  });

  it('counts only high severity findings', () => {
    const findings: MissingClause[] = [
      {
        finding_id: 'uuid-1',
        expected_clause_type: 'termination',
        severity: 'high',
        reason: 'Missing',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        expected_clause_type: 'liability',
        severity: 'high',
        reason: 'Missing',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const counts = countBySeverity(findings);
    expect(counts.high).toBe(2);
    expect(counts.medium).toBe(0);
    expect(counts.low).toBe(0);
  });

  it('counts mixed severity findings', () => {
    const findings: RiskyClause[] = [
      {
        finding_id: 'uuid-1',
        clause_id: 1,
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'high',
        reason: 'Bad',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        clause_id: 2,
        clause_number: '1.2',
        clause_text: 'Test',
        severity: 'high',
        reason: 'Bad',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-3',
        clause_id: 3,
        clause_number: '1.3',
        clause_text: 'Test',
        severity: 'medium',
        reason: 'Questionable',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-4',
        clause_id: 4,
        clause_number: '1.4',
        clause_text: 'Test',
        severity: 'low',
        reason: 'Minor',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const counts = countBySeverity(findings);
    expect(counts.high).toBe(2);
    expect(counts.medium).toBe(1);
    expect(counts.low).toBe(1);
  });

  it('counts duplicate clause_id with different severity separately', () => {
    const findings: RiskyClause[] = [
      {
        finding_id: 'uuid-1',
        clause_id: 1,  // Same clause_id
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'high',
        reason: 'First issue',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-2',
        clause_id: 1,  // Same clause_id, different finding
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'medium',
        reason: 'Second issue',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
      {
        finding_id: 'uuid-3',
        clause_id: 1,  // Same clause_id, third finding
        clause_number: '1.1',
        clause_text: 'Test',
        severity: 'low',
        reason: 'Third issue',
        explanation: 'Explanation',
        formatted_citation: 'Citation',
      },
    ];
    const counts = countBySeverity(findings);
    expect(counts.high).toBe(1);
    expect(counts.medium).toBe(1);
    expect(counts.low).toBe(1);
  });
});
