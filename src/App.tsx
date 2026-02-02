import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClientProvider } from './infrastructure/query/QueryClientProvider';
import { ToastProvider } from './infrastructure/notifications/ToastProvider';
import { useAuth, AuthProvider } from './presentation/contexts/AuthContext';
import { ProtectedRoute } from './presentation/components/auth';
import { Navbar } from './presentation/components/layout';
import { DeviceList, DeviceManagement, DevicePassport, CreatePolicyPage, LoginPage, UsersPage } from './presentation/pages';

function ProtectedLayout(): JSX.Element {
  return (
    <ProtectedRoute>
      <Outlet />
    </ProtectedRoute>
  );
}

/**
 * AppRoutes - Componente interno con las rutas
 */
function AppRoutes(): JSX.Element {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Todas las rutas protegidas bajo un layout */}
      <Route element={<ProtectedLayout />}>
        <Route path="/devices" element={<DeviceList />} />
        <Route path="/devices/:id" element={<DeviceManagement />} />
        <Route path="/devices/:id/passport" element={<DevicePassport />} />
        <Route path="/devices/:id/policies/create" element={<CreatePolicyPage />} />
        <Route path="/users" element={<UsersPage />} />
      </Route>

      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? '/devices' : '/login'} replace />}
      />
    </Routes>
  );
}

export default function App(): JSX.Element {
  return (
    <QueryClientProvider>
      <AuthProvider>
        <ToastProvider />
        <Router>
          <Navbar />
          <AppRoutes />
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}
