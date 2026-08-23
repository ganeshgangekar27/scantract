import { useParams } from 'react-router-dom';

export const ReportPlaceholder: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  
  // Parse as number to verify type correctness
  const contractIdNum = contractId ? Number(contractId) : null;
  
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Report View (Placeholder)
        </h2>
        <p className="text-gray-600 mb-4">
          This page will display the contract risk report once Stage 9 frontend is implemented.
        </p>
        
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <p className="text-sm text-gray-700">
            <strong>Contract ID:</strong> {contractIdNum}
          </p>
          <p className="text-sm text-gray-700">
            <strong>Type:</strong> {typeof contractIdNum === 'number' ? 'number ✓' : 'ERROR: not a number'}
          </p>
        </div>
        
        <div className="mt-6">
          <a href="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Upload
          </a>
        </div>
      </div>
    </div>
  );
};
