import { useState, useEffect } from 'react';
import type { ContractReport } from '../types/report.types';

interface UseContractReportResult {
  report: ContractReport | null;
  loading: boolean;
  error: string | null;
}

export function useContractReport(contractId: number): UseContractReportResult {
  const [report, setReport] = useState<ContractReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`/api/contracts/${contractId}/report`);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Contract not found');
          }
          throw new Error(`Failed to load report: ${response.statusText}`);
        }
        
        const data = await response.json();
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [contractId]);

  return { report, loading, error };
}
