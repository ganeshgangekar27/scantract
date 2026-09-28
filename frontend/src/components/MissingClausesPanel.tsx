import type { MissingClauseReport } from '../types/report.types';
import { useState } from 'react';

interface MissingClausesPanelProps {
  missingClauses: MissingClauseReport[];
}

export function MissingClausesPanel({ missingClauses }: MissingClausesPanelProps) {
  const [expandedClause, setExpandedClause] = useState<string | null>(null);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const toggleExpand = (findingId: string) => {
    setExpandedClause(expandedClause === findingId ? null : findingId);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Missing Clauses</h2>
      
      {missingClauses.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-green-800 font-medium">
              No required clauses are missing from this contract
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {missingClauses.map((clause) => {
            const isExpanded = expandedClause === clause.finding_id;
            
            return (
              <div key={clause.finding_id} className="border border-gray-200 rounded-md overflow-hidden">
                {/* Header */}
                <div className="bg-gray-50 px-4 py-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-gray-900 mb-1">
                        {clause.expected_clause_type}
                      </h3>
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getSeverityColor(clause.severity)}`}>
                        {clause.severity.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Reason */}
                <div className="px-4 py-3 border-b border-gray-200">
                  <p className="text-sm text-gray-700">{clause.reason}</p>
                </div>

                {/* Expandable Details */}
                <div className="px-4 py-2">
                  <button
                    onClick={() => toggleExpand(clause.finding_id)}
                    className="flex items-center justify-between w-full text-sm font-medium text-blue-600 hover:text-blue-800"
                  >
                    <span>{isExpanded ? 'Hide' : 'Show'} Details</span>
                    <svg
                      className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3 border-t border-gray-200 pt-3">
                    {/* Explanation */}
                    <div>
                      <h4 className="text-xs font-semibold text-gray-700 mb-1">Explanation</h4>
                      <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-line">
                        {clause.explanation}
                      </p>
                    </div>

                    {/* Citation */}
                    <div>
                      <h4 className="text-xs font-semibold text-gray-700 mb-1">Legal Reference</h4>
                      <div className="bg-blue-50 border border-blue-200 rounded p-3">
                        <p className="text-xs text-gray-800 leading-relaxed whitespace-pre-line">
                          {clause.formatted_citation}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
