import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Skeleton } from '../components/ui';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Skeleton width="300px" height="200px" />
      </div>
    );
  }
  
  if (!user) {
    // Save current path to return after login
    sessionStorage.setItem('redirect_after_login', location.pathname);
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Skeleton width="300px" height="200px" />
      </div>
    );
  }
  
  if (user) {
    // Check if there's a saved redirect path
    const redirectPath = sessionStorage.getItem('redirect_after_login') || '/dashboard';
    sessionStorage.removeItem('redirect_after_login');
    return <Navigate to={redirectPath} replace />;
  }
  
  return <>{children}</>;
}
