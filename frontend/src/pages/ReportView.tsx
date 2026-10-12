/**
 * ReportView - Display contract analysis results with risk assessment, findings, and filters.
 * 
 * Features:
 * - Risk ring visualization with score/label
 * - Severity filter chips (All/High/Medium/Low)
 * - Risky findings list with clause details
 * - Missing clauses section
 * - PDF download
 * - Click to select/highlight findings
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { Button, Card } from '../components/ui';
import { SeverityBar } from '../components/SeverityBar';
import { getReport, downloadReportPdf, ApiError } from '../lib/api';
import { riskScore, riskLabel, filterBySeverity, countBySeverity, topRisks } from '../lib/risk';
import type { Report } from '../lib/types';

type SeverityFilter = 'all' | 'high' | 'medium' | 'low';

export function ReportView() {
  const { contractId } = useParams<{ contractId: string }>();
  const contractIdNum = parseInt(contractId || '0', 10);

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [reloadCounter, setReloadCounter] = useState(0);
  const [expandedFindingIds, setExpandedFindingIds] = useState<Set<string>>(new Set());
  const [showAllFindings, setShowAllFindings] = useState(false);

  // Load report on mount
  useEffect(() => {
    const loadReport = async () => {
      try {
        setLoading(true);
        const data = await getReport(contractIdNum);
        setReport(data);
        setError(null);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 409) {
            setError('Analysis not finished yet');
          } else if (err.status === 404) {
            setError('Contract not found');
          } else {
            setError(err.message);
          }
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load report');
        }
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, [contractIdNum, reloadCounter]);

  const handleRetry = () => {
    setError(null);
    setReloadCounter(prev => prev + 1);
  };

  const handleDownloadPDF = async () => {
    if (!report) return;

    try {
      setDownloading(true);
      setDownloadError(null);
      
      const blob = await downloadReportPdf(contractIdNum);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${report.filename}-report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Failed to download PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handleFindingClick = (findingId: string) => {
    // Toggle expanded state
    setExpandedFindingIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(findingId)) {
        newSet.delete(findingId);
      } else {
        newSet.add(findingId);
      }
      return newSet;
    });
    
    // Select finding for panel
    setSelectedFindingId(findingId);
    
    // Scroll to finding (guarded for jsdom)
    if (typeof document !== 'undefined') {
      const element = document.getElementById(`finding-${findingId}`);
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // Loading skeleton
  if (loading) {
    return (
      <AppShell title="Contract Report">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-text-secondary">Loading report...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  // Error state
  if (error) {
    return (
      <AppShell title="Contract Report">
        <Card className="p-6 bg-severity-high-bg border-severity-high-border">
          <h3 className="text-lg font-semibold text-severity-high mb-2">Error</h3>
          <p className="text-text-primary mb-4">{error}</p>
          <Button onClick={handleRetry} variant="secondary">
            Retry
          </Button>
        </Card>
      </AppShell>
    );
  }

  // No report
  if (!report) {
    return (
      <AppShell title="Contract Report">
        <div className="text-center py-12">
          <p className="text-text-secondary">Report not found</p>
        </div>
      </AppShell>
    );
  }

  // Calculate metrics
  const score = riskScore(report.risk_summary);
  const label = riskLabel(score);
  const counts = countBySeverity([...report.risky_clauses, ...report.missing_clauses]);
  const riskyCounts = countBySeverity(report.risky_clauses);
  
  // Filter findings
  const filteredFindings = severityFilter === 'all'
    ? report.risky_clauses
    : filterBySeverity(report.risky_clauses, severityFilter);

  return (
    <AppShell title="Contract Report">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <Card className="p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-text-primary mb-1">
                {report.filename}
              </h1>
              <p className="text-sm text-text-secondary">
                Uploaded: {new Date(report.upload_date).toLocaleDateString()}
              </p>
            </div>

            {/* Risk Ring */}
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  {/* Background circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  {/* Progress circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={`${score * 2.51} 251`}
                    className={
                      label === 'High'
                        ? 'text-severity-high'
                        : label === 'Medium'
                        ? 'text-severity-medium'
                        : 'text-severity-low'
                    }
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-text-primary">{score}</span>
                  <span className="text-xs text-text-secondary">/ 100</span>
                </div>
              </div>
              <div>
                <p className="text-sm text-text-secondary">Risk Level</p>
                <p className={`text-lg font-semibold ${
                  label === 'High'
                    ? 'text-severity-high'
                    : label === 'Medium'
                    ? 'text-severity-medium'
                    : 'text-severity-low'
                }`}>
                  {label}
                </p>
              </div>
            </div>
          </div>

          {/* Counts */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{counts.high}</p>
              <p className="text-sm text-text-secondary">High</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{counts.medium}</p>
              <p className="text-sm text-text-secondary">Medium</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{counts.low}</p>
              <p className="text-sm text-text-secondary">Low</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">
                {report.missing_clauses.length}
              </p>
              <p className="text-sm text-text-secondary">Missing</p>
            </div>
          </div>

          {/* Severity Bar */}
          <div className="mb-4">
            <SeverityBar high={counts.high} medium={counts.medium} low={counts.low} />
          </div>

          {/* PDF Download */}
          <div className="flex items-center gap-4">
            <Button
              onClick={handleDownloadPDF}
              disabled={downloading}
              variant="secondary"
            >
              {downloading ? 'Downloading...' : 'Download PDF'}
            </Button>
            {downloadError && (
              <p className="text-sm text-severity-high">{downloadError}</p>
            )}
          </div>
        </Card>

        {/* Top 5 Risks */}
        {(() => {
          const topRiskRows = topRisks(report.risky_clauses, report.missing_clauses, 5);
          if (topRiskRows.length === 0) return null;
          
          return (
            <Card className="p-6 mb-6" data-testid="top-risks">
              <h2 className="text-xl font-semibold text-text-primary mb-4">Top 5 Risks</h2>
              <div className="space-y-3">
                {topRiskRows.map((risk) => (
                  <div
                    key={risk.key}
                    data-testid="top-risk-row"
                    className="flex items-start gap-3 p-3 bg-surface-secondary rounded-lg"
                  >
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        risk.severity === 'high'
                          ? 'bg-severity-high-bg text-severity-high border border-severity-high-border'
                          : risk.severity === 'medium'
                          ? 'bg-severity-medium-bg text-severity-medium border border-severity-medium-border'
                          : 'bg-severity-low-bg text-severity-low border border-severity-low-border'
                      }`}
                    >
                      {risk.severity.toUpperCase()}
                    </span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-text-primary mb-1">{risk.label}</p>
                      <p className="text-sm text-text-secondary">{risk.why}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          );
        })()}

        {/* Filter Chips */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setSeverityFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              severityFilter === 'all'
                ? 'bg-primary text-white'
                : 'bg-surface border border-border text-text-secondary hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            All ({report.risky_clauses.length})
          </button>
          <button
            onClick={() => setSeverityFilter('high')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              severityFilter === 'high'
                ? 'bg-severity-high text-white'
                : 'bg-surface border border-border text-text-secondary hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            High ({riskyCounts.high})
          </button>
          <button
            onClick={() => setSeverityFilter('medium')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              severityFilter === 'medium'
                ? 'bg-severity-medium text-white'
                : 'bg-surface border border-border text-text-secondary hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Medium ({riskyCounts.medium})
          </button>
          <button
            onClick={() => setSeverityFilter('low')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              severityFilter === 'low'
                ? 'bg-severity-low text-white'
                : 'bg-surface border border-border text-text-secondary hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Low ({riskyCounts.low})
          </button>
        </div>

        {/* Why Flagged Panel */}
        <Card className="p-6 mb-6 sticky top-4 z-10 lg:hidden">
          {selectedFindingId ? (
            (() => {
              const selected = report.risky_clauses.find(f => f.finding_id === selectedFindingId);
              if (!selected) return null;
              return (
                <>
                  <h3 className="text-lg font-bold text-text-primary mb-2">Why Flagged</h3>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-semibold text-text-secondary mb-1">Reason</p>
                      <p className="text-text-primary">{selected.reason}</p>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-secondary mb-1">Explanation</p>
                      <p className="text-text-secondary">{selected.explanation}</p>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-secondary mb-1">Legal Reference</p>
                      <p className="text-text-tertiary text-sm">{selected.formatted_citation}</p>
                    </div>
                  </div>
                </>
              );
            })()
          ) : (
            <p className="text-text-secondary text-center">
              Select a finding to see why it was flagged
            </p>
          )}
        </Card>

        {/* Two-column layout for desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Findings */}
          <div className="lg:col-span-2 space-y-4">
            {/* Risky Findings */}
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-text-primary">Risky Clauses</h2>
              {filteredFindings.length === 0 ? (
                <Card className="p-6 text-center">
                  <p className="text-text-secondary">
                    No {severityFilter !== 'all' ? severityFilter + ' ' : ''}findings found
                  </p>
                </Card>
              ) : (
                <>
                  {(showAllFindings ? filteredFindings : filteredFindings.slice(0, 5)).map((finding) => {
                    const isExpanded = expandedFindingIds.has(finding.finding_id);
                    return (
                      <Card
                        key={finding.finding_id}
                        id={`finding-${finding.finding_id}`}
                        data-testid="finding-card"
                        aria-expanded={isExpanded}
                        className={`p-6 cursor-pointer transition-all ${
                          selectedFindingId === finding.finding_id
                            ? 'ring-2 ring-primary'
                            : 'hover:shadow-md'
                        }`}
                        onClick={() => handleFindingClick(finding.finding_id)}
                      >
                        <div className="flex items-start gap-4">
                          {/* Severity Badge */}
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
                              finding.severity === 'high'
                                ? 'bg-severity-high-bg text-severity-high'
                                : finding.severity === 'medium'
                                ? 'bg-severity-medium-bg text-severity-medium'
                                : 'bg-severity-low-bg text-severity-low'
                            }`}
                          >
                            {finding.severity}
                          </span>

                          <div className="flex-1">
                            {/* Clause Number - always visible */}
                            <p className="text-sm font-semibold text-text-secondary mb-2">
                              Clause {finding.clause_number}
                            </p>

                            {/* Expanded content */}
                            {isExpanded && (
                              <div data-testid="finding-details">
                                {/* Clause Text */}
                                <p className="text-text-primary mb-3 italic">
                                  "{finding.clause_text}"
                                </p>

                                {/* Explanation */}
                                <p className="text-text-secondary mb-3">
                                  {finding.explanation}
                                </p>

                                {/* Citation */}
                                <p className="text-sm text-text-tertiary">
                                  {finding.formatted_citation}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                  
                  {/* Show all button */}
                  {!showAllFindings && filteredFindings.length > 5 && (
                    <Button
                      onClick={() => setShowAllFindings(true)}
                      variant="secondary"
                      className="w-full"
                    >
                      Show all {filteredFindings.length}
                    </Button>
                  )}
                </>
              )}
            </div>

            {/* Missing Clauses */}
            {report.missing_clauses.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-text-primary">Missing Clauses</h2>
                {report.missing_clauses.map((missing) => (
                  <Card key={missing.finding_id} className="p-6">
                    <div className="flex items-start gap-4">
                      {/* Severity Badge */}
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
                          missing.severity === 'high'
                            ? 'bg-severity-high-bg text-severity-high'
                            : missing.severity === 'medium'
                            ? 'bg-severity-medium-bg text-severity-medium'
                            : 'bg-severity-low-bg text-severity-low'
                        }`}
                      >
                        {missing.severity}
                      </span>

                      <div className="flex-1">
                        {/* Expected Clause Type */}
                        <p className="text-lg font-semibold text-text-primary mb-2">
                          {missing.expected_clause_type}
                        </p>

                        {/* Reason */}
                        <p className="text-text-primary font-medium mb-2">
                          {missing.reason}
                        </p>

                        {/* Explanation */}
                        <p className="text-text-secondary mb-3">
                          {missing.explanation}
                        </p>

                        {/* Citation */}
                        <p className="text-sm text-text-tertiary">
                          {missing.formatted_citation}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Right: Why Flagged Panel (desktop only) */}
          <div className="hidden lg:block">
            <Card className="p-6 sticky top-4">
              {selectedFindingId ? (
                (() => {
                  const selected = report.risky_clauses.find(f => f.finding_id === selectedFindingId);
                  if (!selected) return null;
                  return (
                    <>
                      <h3 className="text-lg font-bold text-text-primary mb-4">Why Flagged</h3>
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm font-semibold text-text-secondary mb-1">Reason</p>
                          <p className="text-text-primary">{selected.reason}</p>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-text-secondary mb-1">Explanation</p>
                          <p className="text-text-secondary">{selected.explanation}</p>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-text-secondary mb-1">Legal Reference</p>
                          <p className="text-text-tertiary text-sm">{selected.formatted_citation}</p>
                        </div>
                      </div>
                    </>
                  );
                })()
              ) : (
                <p className="text-text-secondary text-center py-8">
                  Select a finding to see why it was flagged
                </p>
              )}
            </Card>
          </div>
        </div>

        {/* Disclaimer */}
        <Card className="p-4 bg-background-secondary">
          <p className="text-sm text-text-secondary text-center">
            ScanTract is an educational tool, not legal advice. The knowledge base is sample
            data and has not been verified by a lawyer.
          </p>
        </Card>
      </div>
    </AppShell>
  );
}
