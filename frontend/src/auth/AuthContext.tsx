import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { apiRequest } from '../lib/api';

// Match auth.py exact field names
interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

interface RegisterResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    created_at: string;
  };
}

interface LoginPayload {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
  is_active: boolean;
}

interface ForgotPasswordPayload {
  email: string;
}

interface ForgotPasswordResponse {
  message: string;
  demo_reset_link?: string;
}

interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  forgotPassword: (email: string) => Promise<ForgotPasswordResponse>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'scantract_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Load user on mount if token exists
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem(TOKEN_KEY);
      
      if (!token) {
        setLoading(false);
        return;
      }
      
      try {
        const userData = await apiRequest<User>('/api/auth/me');
        setUser(userData);
      } catch (error) {
        console.error('Failed to load user:', error);
        localStorage.removeItem(TOKEN_KEY);
      } finally {
        setLoading(false);
      }
    };
    
    loadUser();
  }, []);
  
  const login = async (email: string, password: string) => {
    const payload: LoginPayload = { email, password };
    const response = await apiRequest<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    
    localStorage.setItem(TOKEN_KEY, response.access_token);
    
    // Load user info
    const userData = await apiRequest<User>('/api/auth/me');
    setUser(userData);
  };
  
  const register = async (email: string, password: string, fullName: string) => {
    const payload: RegisterPayload = { 
      email, 
      password, 
      full_name: fullName 
    };
    
    const response = await apiRequest<RegisterResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    
    localStorage.setItem(TOKEN_KEY, response.access_token);
    
    // Set user from registration response
    setUser({
      id: response.user.id,
      email: response.user.email,
      full_name: response.user.full_name,
      created_at: response.user.created_at,
      is_active: true,
    });
  };
  
  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };
  
  const forgotPassword = async (email: string): Promise<ForgotPasswordResponse> => {
    const payload: ForgotPasswordPayload = { email };
    return await apiRequest<ForgotPasswordResponse>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  };
  
  const resetPassword = async (token: string, newPassword: string) => {
    const payload: ResetPasswordPayload = { token, new_password: newPassword };
    await apiRequest('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  };
  
  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      register,
      logout,
      forgotPassword,
      resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
