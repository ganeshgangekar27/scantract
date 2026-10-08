/**
 * API client with authentication and error handling
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  status: number;
  fieldErrors?: Record<string, string[]>;
  
  constructor(
    status: number,
    message: string,
    fieldErrors?: Record<string, string[]>
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

interface FastAPIValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

interface PipelineError {
  message?: string;
  failed_stage?: string;
  error_message?: string;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Attach Authorization header if token exists
  const token = localStorage.getItem('scantract_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Handle 401 Unauthorized
  if (response.status === 401) {
    const isAuthEndpoint = endpoint.startsWith('/api/auth/login') || 
                          endpoint.startsWith('/api/auth/register') ||
                          endpoint.startsWith('/api/auth/forgot-password') ||
                          endpoint.startsWith('/api/auth/reset-password');
    
    if (!isAuthEndpoint) {
      // Clear session and redirect
      localStorage.removeItem('scantract_token');
      
      // Show toast if available
      if (typeof window !== 'undefined' && 'toast' in window) {
        (window as any).toast?.error('Session expired, please log in again');
      }
      
      // Redirect to login
      const currentPath = window.location.pathname;
      if (currentPath !== '/login') {
        sessionStorage.setItem('redirect_after_login', currentPath);
        window.location.href = '/login';
      }
    }
  }
  
  // Parse response
  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');
  
  if (!isJson) {
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`);
    }
    return (await response.text()) as T;
  }
  
  const data = await response.json();
  
  if (!response.ok) {
    // Handle FastAPI validation errors (422)
    if (response.status === 422 && Array.isArray(data.detail)) {
      const validationErrors: FastAPIValidationError[] = data.detail;
      const fieldErrors: Record<string, string[]> = {};
      
      validationErrors.forEach((err) => {
        const field = err.loc[err.loc.length - 1].toString();
        if (!fieldErrors[field]) {
          fieldErrors[field] = [];
        }
        fieldErrors[field].push(err.msg);
      });
      
      throw new ApiError(422, 'Validation error', fieldErrors);
    }
    
    // Handle FastAPI detail string
    if (typeof data.detail === 'string') {
      throw new ApiError(response.status, data.detail);
    }
    
    // Handle pipeline error object
    if (data.detail && typeof data.detail === 'object') {
      const pipelineError = data.detail as PipelineError;
      const message = pipelineError.message || 
                     pipelineError.error_message || 
                     `Error at stage: ${pipelineError.failed_stage}`;
      throw new ApiError(response.status, message);
    }
    
    // Generic error
    throw new ApiError(response.status, data.error || 'An error occurred');
  }
  
  // Handle {success, data, error} envelope
  if (typeof data === 'object' && 'success' in data) {
    if (!data.success) {
      throw new ApiError(response.status, data.error || 'Request failed');
    }
    return data.data as T;
  }
  
  // Return raw data
  return data as T;
}

/**
 * Upload a file via multipart/form-data
 */
export async function apiUpload<T>(
  endpoint: string,
  file: File,
  additionalData?: Record<string, string>
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = localStorage.getItem('scantract_token');
  
  const formData = new FormData();
  formData.append('file', file);
  
  if (additionalData) {
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value);
    });
  }
  
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    if (typeof data.detail === 'string') {
      throw new ApiError(response.status, data.detail);
    }
    throw new ApiError(response.status, data.error || 'Upload failed');
  }
  
  if (typeof data === 'object' && 'success' in data) {
    if (!data.success) {
      throw new ApiError(response.status, data.error || 'Upload failed');
    }
    return data.data as T;
  }
  
  return data as T;
}
