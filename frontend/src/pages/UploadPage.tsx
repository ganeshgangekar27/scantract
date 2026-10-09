/**
 * UploadPage - Contract upload with drag-drop, validation, and live pipeline tracking.
 * 
 * - Accepts .pdf and .docx files up to 15 MB
 * - Shows upload progress
 * - Polls pipeline status after upload
 * - Navigates to report on completion
 * - No contract_type selector (backend defaults to 'rental')
 */

import { useState, useRef, type DragEvent, type ChangeEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { Button, Card } from '../components/ui';
import { PipelineTracker } from '../components/PipelineTracker';
import { usePipelinePolling } from '../hooks/usePipelinePolling';
import { uploadContract } from '../lib/api';
import type { UploadResponse } from '../lib/types';

const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contractId, setContractId] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Poll pipeline status after upload
  const { data: pipelineData, error: pipelineError, isTimeout } = usePipelinePolling(contractId);

  // Navigate to report when completed
  if (pipelineData?.processing_status === 'completed' && contractId) {
    navigate(`/contracts/${contractId}`);
  }

  const validateFile = (file: File): string | null => {
    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return 'Invalid file type. Only PDF and DOCX files are supported.';
    }

    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds maximum allowed size of 15MB';
    }

    return null;
  };

  const handleFileSelect = (selectedFile: File) => {
    setError(null);

    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setFile(selectedFile);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response: UploadResponse = await uploadContract(file);
      setContractId(response.contract_id);
      setUploading(false);
    } catch (err) {
      setUploading(false);

      // Handle 401 - redirect to login
      if (err instanceof Error && err.message.includes('401')) {
        const currentPath = window.location.pathname;
        sessionStorage.setItem('redirect_after_login', currentPath);
        navigate('/login');
        return;
      }

      // Handle 429 or quota errors - show friendly message from API
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
    }
  };

  const handleRetry = () => {
    setFile(null);
    setContractId(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getDropZoneClasses = () => {
    const base = 'border-2 border-dashed rounded-lg p-12 text-center transition-all cursor-pointer';

    if (isDragging) {
      return `${base} border-primary bg-primary/5`;
    }

    if (error) {
      return `${base} border-severity-high bg-severity-high-bg`;
    }

    return `${base} border-border hover:border-primary hover:bg-primary/5`;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Show pipeline tracker if upload is complete and polling
  if (contractId && !uploading) {
    return (
      <AppShell title="Processing Contract">
        <div className="max-w-4xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-text-primary mb-2">Processing Your Contract</h1>
          <p className="text-text-secondary mb-8">
            {file?.name || 'Your contract'} is being analyzed
          </p>

          {isTimeout && (
            <Card className="mb-6 p-4 bg-severity-medium-bg border border-severity-medium-border">
              <p className="text-severity-medium font-medium">
                Processing is taking longer than expected. Please check back later.
              </p>
            </Card>
          )}

          {pipelineError && (
            <Card className="mb-6 p-4 bg-severity-high-bg border border-severity-high-border">
              <p className="text-severity-high font-medium">{pipelineError}</p>
            </Card>
          )}

          <PipelineTracker
            stage={pipelineData?.pipeline_stage || null}
            status={pipelineData?.processing_status || 'processing'}
            failedStage={pipelineData?.failed_stage}
            errorMessage={pipelineData?.error_message}
            onRetry={handleRetry}
          />

          <div className="mt-6 text-center">
            <Button variant="secondary" onClick={() => navigate('/contracts')}>
              View All Contracts
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Upload Contract">
      <div className="max-w-2xl mx-auto p-6">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Upload Contract</h1>
        <p className="text-text-secondary mb-8">
          Upload a rental or freelance contract for AI-powered risk analysis
        </p>

        {/* Free tier notice */}
        <Card className="mb-6 p-4 bg-background-secondary border border-border">
          <p className="text-sm text-text-secondary">
            <strong>Free AI tier:</strong> About 2 analyses per day.{' '}
            <Link to="/contracts" className="text-primary hover:underline">
              Sample contracts are always available
            </Link>
          </p>
        </Card>

        {error && (
          <Card className="mb-6 p-4 bg-severity-high-bg border border-severity-high-border">
            <p className="text-severity-high font-medium">{error}</p>
          </Card>
        )}

        {!file && !uploading && (
          <div
            className={getDropZoneClasses()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
          >
            <svg
              className="w-16 h-16 mx-auto mb-4 text-text-tertiary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>

            <p className="text-lg text-text-primary mb-2">
              Drag and drop your contract here
            </p>
            <p className="text-sm text-text-secondary mb-4">or</p>
            <Button
              variant="primary"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              Browse Files
            </Button>
            <p className="text-xs text-text-tertiary mt-4">
              Supported formats: PDF, DOCX (max 15MB)
            </p>

            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx"
              onChange={handleInputChange}
              data-testid="file-input"
            />
          </div>
        )}

        {file && !uploading && !contractId && (
          <Card className="p-6">
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary mb-1">{file.name}</p>
                <p className="text-xs text-text-secondary">{formatFileSize(file.size)}</p>
              </div>
              <Button
                variant="ghost"
                onClick={handleRetry}
                className="text-text-tertiary hover:text-text-primary"
              >
                Remove
              </Button>
            </div>

            <Button onClick={handleUpload} className="w-full">
              Analyze Contract
            </Button>
          </Card>
        )}

        {uploading && (
          <Card className="p-6">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-text-primary font-medium">Uploading...</p>
              <p className="text-sm text-text-secondary mt-2">{file?.name}</p>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

