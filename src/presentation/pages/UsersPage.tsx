/**
 * UsersPage - Página de gestión de usuarios (solo admin)
 */
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../hooks';
import { AdminRoute } from '../components/auth';

export default function UsersPage(): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  return (
    <AdminRoute>
      <div style={{ padding: isMobile ? '1rem' : '2rem' }}>
        <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem' }}>
          {t('users.title') || 'Gestión de Usuarios'}
        </h1>
        <p style={{ marginTop: '1rem', color: '#666' }}>
          {t('users.comingSoon') || 'Próximamente: Funcionalidad de gestión de usuarios'}
        </p>
      </div>
    </AdminRoute>
  );
}
