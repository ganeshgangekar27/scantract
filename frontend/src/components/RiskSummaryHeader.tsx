import type { ContractReport } from '../types/report.types';
import { usePDFDownload } from '../hooks/usePDFDownload';
import { useState } from 'react';

interface RiskSummaryHeaderProps {
  report: ContractReport;
  contractId: number;
}

export function RiskSummaryHeader({ report, contractId }: RiskSummaryHeaderProps) {
  const { downloadPDF, downloading, error: pdfError } = usePDFDownload(contractId, report.filename);
  const [showError, setShowError] = useState(false);

  const handleDownload = async () => {
    try {
      await downloadPDF();
    } catch (err) {
      setShowError(true);
      setTimeout(() => setShowError(false), 5000); // Hide error after 5s
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'none':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      {/* Error Alert */}
      {showError && pdfError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{pdfError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{report.filename}</h1>
          <p className="text-sm text-gray-600">Uploaded on {formatDate(report.upload_date)}</p>
        </div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="mt-4 md:mt-0 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {downloading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Downloading...
            </>
          ) : (
            <>
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download PDF
            </>
          )}
        </button>
      </div>

      {/* Risk Level Badge and Counts */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <span className="text-sm font-medium text-gray-600 mr-2">Overall Risk:</span>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRiskLevelColor(report.risk_summary.overall_risk_level)}`}>
            {report.risk_summary.overall_risk_level.toUpperCase()}
          </span>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">Total Clauses:</span>
            <span className="ml-1 text-gray-900">{report.risk_summary.total_clauses}</span>
          </div>
          <div>
            <span className="font-medium text-red-600">High:</span>
            <span className="ml-1 text-gray-900">{report.risk_summary.high_severity_count}</span>
          </div>
          <div>
            <span className="font-medium text-yellow-600">Medium:</span>
            <span className="ml-1 text-gray-900">{report.risk_summary.medium_severity_count}</span>
          </div>
          <div>
            <span className="font-medium text-blue-600">Low:</span>
            <span className="ml-1 text-gray-900">{report.risk_summary.low_severity_count}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
