import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { UploadState, UploadResponse, APIResponse, ValidationResult } from '../types/upload.types';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
];
const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB in bytes
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface ContractUploadProps {
  onUploadComplete?: (contractId: number) => void;
}

export const ContractUpload: React.FC<ContractUploadProps> = ({ onUploadComplete }) => {
  const [state, setState] = useState<UploadState>({
    file: null,
    uploading: false,
    uploadProgress: 0,
    processing: false,
    error: null
  });
  
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  
  // Validation functions
  const validateFileType = (file: File): ValidationResult => {
    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    const isValidExtension = ALLOWED_EXTENSIONS.includes(extension);
    const isValidMimeType = ALLOWED_MIME_TYPES.includes(file.type);
    
    if (!isValidExtension || !isValidMimeType) {
      return {
        isValid: false,
        error: 'Only PDF and DOCX files are supported'
      };
    }
    
    return { isValid: true, error: null };
  };
  
  const validateFileSize = (file: File): ValidationResult => {
    if (file.size > MAX_FILE_SIZE) {
      return {
        isValid: false,
        error: 'File size must be under 15MB'
      };
    }
    
    return { isValid: true, error: null };
  };
  
  const validateFile = (file: File): ValidationResult => {
    const typeValidation = validateFileType(file);
    if (!typeValidation.isValid) {
      return typeValidation;
    }
    
    const sizeValidation = validateFileSize(file);
    if (!sizeValidation.isValid) {
      return sizeValidation;
    }
    
    return { isValid: true, error: null };
  };
  
  // Upload function using XMLHttpRequest for progress tracking
  // Note: We use XMLHttpRequest instead of fetch() because the Fetch API does not
  // support upload progress events. The xhr.upload.addEventListener('progress', ...)
  // allows us to track and display real-time upload progress to the user, which is
  // critical for large contract files (up to 15MB). Once the File System Access API
  // or fetch() gains progress event support, we can migrate to the more modern API.
  const uploadFile = (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = (e.loaded / e.total) * 100;
          setState(prev => ({ ...prev, uploadProgress: Math.round(percent) }));
        }
      });
      
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          try {
            const response: APIResponse<UploadResponse> = JSON.parse(xhr.responseText);
            if (response.success && response.data) {
              resolve(response.data);
            } else {
              reject(new Error(response.error || 'Upload failed'));
            }
          } catch (error) {
            reject(new Error('Failed to parse response'));
          }
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });
      
      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });
      
      xhr.open('POST', `${API_BASE_URL}/api/contracts/upload`);
      xhr.send(formData);
    });
  };
  
  // Event handlers
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };
  
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };
  
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };
  
  const processFile = async (file: File) => {
    // Clear previous errors
    setState(prev => ({ ...prev, error: null }));
    
    // Validate file
    const validation = validateFile(file);
    if (!validation.isValid) {
      setState(prev => ({ ...prev, error: validation.error }));
      return;
    }
    
    // Set file and start upload
    setState(prev => ({ ...prev, file, uploading: true, uploadProgress: 0 }));
    
    try {
      const response = await uploadFile(file);
      
      // Upload successful
      setState(prev => ({ ...prev, uploading: false, processing: true }));
      
      // Call optional callback
      if (onUploadComplete) {
        onUploadComplete(response.contract_id);
      }
      
      // Navigate to report view
      navigate(`/report/${response.contract_id}`);
    } catch (error) {
      setState(prev => ({
        ...prev,
        uploading: false,
        uploadProgress: 0,
        error: error instanceof Error ? error.message : 'Upload failed'
      }));
    }
  };
  
  const handleRetry = () => {
    setState({
      file: null,
      uploading: false,
      uploadProgress: 0,
      processing: false,
      error: null
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // Determine drop zone classes
  const getDropZoneClasses = () => {
    const baseClasses = 'border-2 rounded-lg p-12 text-center transition-all cursor-pointer';
    
    if (state.error) {
      return `${baseClasses} border-red-400 bg-red-50 border-dashed`;
    }
    
    if (isDragging) {
      return `${baseClasses} border-blue-600 bg-blue-100 border-solid`;
    }
    
    if (state.uploading || state.processing) {
      return `${baseClasses} border-gray-300 bg-gray-50 border-dashed opacity-50 cursor-not-allowed`;
    }
    
    return `${baseClasses} border-gray-300 bg-gray-50 border-dashed hover:border-blue-400 hover:bg-blue-50`;
  };
  
  return (
    <div className="container mx-auto max-w-2xl p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Contract</h1>
      <p className="text-gray-600 mb-8">
        Upload a rental or freelance contract for risk analysis
      </p>
      
      {/* Error message */}
      {state.error && (
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded mb-4" role="alert">
          <p className="font-medium">{state.error}</p>
        </div>
      )}
      
      {/* Drop zone */}
      {!state.uploading && !state.processing && (
        <div
          className={getDropZoneClasses()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          role="button"
          tabIndex={0}
          aria-label="Upload contract file"
        >
          <div className="flex flex-col items-center">
            <svg
              className="w-16 h-16 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            
            <p className="text-lg text-gray-700 mb-2">
              Drag and drop your contract here or click to browse
            </p>
            
            <p className="text-sm text-gray-500 mb-4">
              Supported formats: PDF, DOCX (max 15MB)
            </p>
            
            <button
              type="button"
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              Browse Files
            </button>
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.docx"
            onChange={handleFileSelect}
            aria-label="Upload contract file"
          />
        </div>
      )}
      
      {/* Upload progress */}
      {state.uploading && (
        <div className="bg-white border border-gray-300 rounded-lg p-8">
          <p className="text-sm text-gray-700 mb-2">
            Uploading... {state.uploadProgress}%
          </p>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${state.uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600">
            {state.file?.name}
          </p>
        </div>
      )}
      
      {/* Processing state */}
      {state.processing && (
        <div className="bg-white border border-gray-300 rounded-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-lg text-gray-700">Processing...</p>
          <p className="text-sm text-gray-600 mt-2">
            Redirecting to analysis results
          </p>
        </div>
      )}
      
      {/* Retry button */}
      {state.error && (
        <div className="mt-4 text-center">
          <button
            type="button"
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded font-medium"
            onClick={handleRetry}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
