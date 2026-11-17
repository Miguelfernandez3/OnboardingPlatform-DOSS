import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';
import { useAuth } from '../../contexts/AuthContext';
import UserAccountMenu from './UserAccountMenu';

/**
 * Navbar - Componente de navegación
 */
export default function Navbar(): JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { isAuthenticated, isAdmin, user, logout } = useAuth();

  const isActive = (path: string): boolean => location.pathname === path;

  // Ocultar navbar en página de login
  if (location.pathname === '/login') {
    return <></>;
  }

  const handleLogout = (): void => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <nav style={{
      backgroundColor: '#343a40',
      padding: isMobile ? '0.75rem 1rem' : '1rem 2rem',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: isMobile ? '0.5rem' : '2rem'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: isMobile ? '0.5rem' : '2rem'
        }}>
          <Link
            to="/devices"
            style={{
              color: 'white',
              textDecoration: 'none',
              fontSize: isMobile ? '1.1rem' : '1.5rem',
              fontWeight: 'bold'
            }}
          >
            {t('navbar.title')}
          </Link>
          {!isMobile && isAuthenticated && (
            <div style={{ display: 'flex', gap: '1rem' }}>
              <Link
                to="/devices"
                style={{
                  color: isActive('/devices') ? '#ffc107' : 'white',
                  textDecoration: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  backgroundColor: isActive('/devices') ? 'rgba(255, 193, 7, 0.2)' : 'transparent'
                }}
              >
                {t('navbar.devices')}
              </Link>
              {isAdmin && (
                <Link
                  to="/users"
                  style={{
                    color: isActive('/users') ? '#ffc107' : 'white',
                    textDecoration: 'none',
                    padding: '0.5rem 1rem',
                    borderRadius: '4px',
                    backgroundColor: isActive('/users') ? 'rgba(255, 193, 7, 0.2)' : 'transparent'
                  }}
                >
                  {t('navbar.users')}
                </Link>
              )}
              {isAdmin && (
                <Link
                  to="/admin/enforcement"
                  style={{
                    color: isActive('/admin/enforcement') ? '#ffc107' : 'white',
                    textDecoration: 'none',
                    padding: '0.5rem 1rem',
                    borderRadius: '4px',
                    backgroundColor: isActive('/admin/enforcement') ? 'rgba(255, 193, 7, 0.2)' : 'transparent'
                  }}
                >
                  {t('navbar.enforcement')}
                </Link>
              )}
            </div>
          )}
        </div>

        {isAuthenticated && user && (
          <UserAccountMenu userEmail={user.email} isAdmin={isAdmin} onLogout={handleLogout} />
        )}
      </div>
    </nav>
  );
}
