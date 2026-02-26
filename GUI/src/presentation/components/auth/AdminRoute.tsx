/**
 * AdminRoute - Componente que protege rutas requiriendo rol admin
 */
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import ProtectedRoute from './ProtectedRoute';

interface AdminRouteProps {
  children: React.ReactNode;
}

export default function AdminRoute({ children }: AdminRouteProps): JSX.Element {
  const { isAdmin } = useAuth();

  if (!isAdmin) {
    return <Navigate to="/devices" replace />;
  }

  return <ProtectedRoute>{children}</ProtectedRoute>;
}
