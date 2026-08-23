import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ContractUpload } from './components/ContractUpload';
import { ReportPlaceholder } from './pages/ReportPlaceholder';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">ScanTract</h1>
            <p className="text-sm text-gray-600">Contract Risk Analysis</p>
          </div>
        </header>
        
        {/* Routes */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<ContractUpload />} />
            <Route path="/upload" element={<Navigate to="/" replace />} />
            <Route path="/report/:contractId" element={<ReportPlaceholder />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
