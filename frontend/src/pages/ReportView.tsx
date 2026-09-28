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
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <svg className="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-600">Loading report...</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading report</h3>
            <p className="mt-2 text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }
  
  // No report (shouldn't happen if no error)
  if (!report) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Report not found</p>
      </div>
    );
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
