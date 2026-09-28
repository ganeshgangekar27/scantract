import { useState } from 'react';

interface UsePDFDownloadResult {
  downloadPDF: () => Promise<void>;
  downloading: boolean;
  error: string | null;
}

export function usePDFDownload(contractId: number, filename: string): UsePDFDownloadResult {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const downloadPDF = async () => {
    try {
      setDownloading(true);
      setError(null);
      
      const response = await fetch(`/api/contracts/${contractId}/report/pdf`);
      
      if (!response.ok) {
        // CRITICAL: Handle 500 gracefully for Windows dev environments
        if (response.status === 500) {
          throw new Error('PDF generation is currently unavailable. This feature requires Docker deployment.');
        }
        throw new Error(`Failed to download PDF: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}_report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      throw err; // Re-throw so caller can handle if needed
    } finally {
      setDownloading(false);
    }
  };

  return { downloadPDF, downloading, error };
}
