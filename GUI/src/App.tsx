import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { QueryClientProvider } from './infrastructure/query/QueryClientProvider';
import { ToastProvider } from './infrastructure/notifications/ToastProvider';
import { useAuth, AuthProvider } from './presentation/contexts/AuthContext';
import { ProtectedRoute } from './presentation/components/auth';
import { Navbar, LogPanel } from './presentation/components/layout';
import { useIsMobile } from './presentation/hooks';

// Ancho del panel de logs; el contenido se desplaza este ancho al abrirlo (en desktop).
const LOG_PANEL_WIDTH = 480;
import {
  DeviceList,
  DeviceManagement,
  DevicePassport,
  CreatePolicyPage,
  EnforcementAdminPage,
  LoginPage,
  UsersPage,
  NotificationsPage,
  SettingsPage
} from './presentation/pages';

/**
 * Shell - envuelve Navbar + rutas y añade el panel de logs (solo admin, fuera de /login).
 * Al abrir el panel, empuja el contenido a la derecha (en desktop) en vez de taparlo.
 * Debe vivir dentro de Router + AuthProvider.
 */
function Shell(): JSX.Element {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const location = useLocation();
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(false);

  const canShow = isAdmin && location.pathname !== '/login';
  // En móvil el panel es overlay a pantalla completa, no empuja.
  const shift = canShow && open && !isMobile ? LOG_PANEL_WIDTH : 0;

  return (
    <>
      {canShow && !open && (
        <button
          onClick={() => setOpen(true)}
          className="log-panel-tab"
          style={{
            position: 'fixed',
            left: 0,
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: 999,
            backgroundColor: '#343a40',
            color: 'white',
            border: 'none',
            borderRadius: '0 6px 6px 0',
            padding: '0.75rem 0.4rem',
            cursor: 'pointer',
            writingMode: 'vertical-rl',
            letterSpacing: '0.05em',
            fontSize: '0.8rem',
          }}
        >
          {t('serviceLogs.toggle')}
        </button>
      )}
      {canShow && <LogPanel open={open} onClose={() => setOpen(false)} />}
      <div style={{ marginLeft: shift, transition: 'margin-left 0.2s ease' }}>
        <Navbar />
        <AppRoutes />
      </div>
    </>
  );
}

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
        <Route path="/notifications" element={<NotificationsPage key="notif-unread" readFilter="unread" />} />
        <Route path="/notifications/read" element={<NotificationsPage key="notif-read" readFilter="read" />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/admin/enforcement" element={<EnforcementAdminPage />} />
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
          <Shell />
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}
