import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';
import { useAuth } from '../../contexts/AuthContext';
import LanguageSelector from '../common/LanguageSelector';

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

  const handleLogout = () => {
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
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {isAuthenticated && user && (
            <span style={{ color: 'white', fontSize: '0.875rem' }}>
              {t('navbar.welcome', { email: user.email })}
            </span>
          )}
          {isAuthenticated && (
            <button
              onClick={handleLogout}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'transparent',
                color: 'white',
                border: '1px solid white',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              {t('navbar.logout')}
            </button>
          )}
          <LanguageSelector />
        </div>
      </div>
    </nav>
  );
}

