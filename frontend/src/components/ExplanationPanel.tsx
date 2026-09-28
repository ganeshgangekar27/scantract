import type { RiskyClauseReport } from '../types/report.types';

interface ExplanationPanelProps {
  clause: RiskyClauseReport | null;
  onClose: () => void;
}

export function ExplanationPanel({ clause, onClose }: ExplanationPanelProps) {
  if (!clause) {
    return null;
  }

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

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-full lg:w-96 bg-white shadow-xl z-50 overflow-y-auto animate-slide-in">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Risk Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close panel"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Clause Number and Severity */}
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-gray-100 text-gray-800">
              Clause {clause.clause_number}
            </span>
            <span className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium ${getSeverityColor(clause.severity)}`}>
              {clause.severity.toUpperCase()}
            </span>
          </div>

          {/* Clause Text */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Clause Text</h3>
            <blockquote className="border-l-4 border-gray-300 pl-4 py-2 italic text-gray-700 bg-gray-50 rounded-r">
              {clause.clause_text}
            </blockquote>
          </div>

          {/* Why This is Risky */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Why This is Risky</h3>
            <p className="text-gray-900 leading-relaxed">{clause.reason}</p>
          </div>

          {/* Detailed Explanation */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Detailed Explanation</h3>
            <p className="text-gray-900 leading-relaxed whitespace-pre-line">{clause.explanation}</p>
          </div>

          {/* Legal Reference */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Legal Reference</h3>
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-line">
                {clause.formatted_citation}
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
