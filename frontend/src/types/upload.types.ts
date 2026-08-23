/**
 * Upload component state interface.
 */
export interface UploadState {
  file: File | null;
  uploading: boolean;
  uploadProgress: number;  // 0-100
  processing: boolean;
  error: string | null;
}

/**
 * Backend upload response shape.
 * 
 * NOTE: contract_id is INTEGER (number), not UUID string.
 * Matches backend contracts table schema.
 */
export interface UploadResponse {
  contract_id: number;  // INTEGER from database
  filename: string;
  size: number;  // bytes
  upload_timestamp: string;  // ISO datetime
  status: string;  // e.g., "uploaded", "processing"
}

/**
 * Standard API response envelope.
 * 
 * Used across all ScanTract backend endpoints.
 */
export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

/**
 * File validation result.
 */
export interface ValidationResult {
  isValid: boolean;
  error: string | null;
}
