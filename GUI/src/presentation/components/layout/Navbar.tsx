import { useState, useRef, useEffect } from 'react';
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
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const isActive = (path: string): boolean => location.pathname === path;

  // Cerrar menú al hacer clic fuera
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Ocultar navbar en página de login
  if (location.pathname === '/login') {
    return <></>;
  }

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
    setIsMenuOpen(false);
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

        {/* Menú hamburguesa para usuario, idioma y logout */}
        <div ref={menuRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Menu"
            style={{
              background: 'transparent',
              border: '1px solid white',
              borderRadius: '4px',
              cursor: 'pointer',
              padding: '0.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              backgroundColor: '#ffffff',
              borderRadius: '1px',
            }} />
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              backgroundColor: '#ffffff',
              borderRadius: '1px',
            }} />
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              backgroundColor: '#ffffff',
              borderRadius: '1px',
            }} />
          </button>

          {/* Dropdown Menu */}
          {isMenuOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: '0',
              backgroundColor: '#343a40',
              borderRadius: '4px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              minWidth: '220px',
              overflow: 'hidden',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              zIndex: 1000,
            }}>
              {/* Usuario Info */}
              {isAuthenticated && user && (
                <div style={{
                  padding: '0.75rem 1rem',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                }}>
                  <div style={{ color: 'white', fontSize: '0.875rem' }}>
                    {t('navbar.welcome', { email: user.email })}
                  </div>
                </div>
              )}

              {/* Selector de idioma */}
              <div style={{
                padding: '0.75rem 1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              }}>
                <span style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.875rem' }}>
                  {t('navbar.language')}
                </span>
                <LanguageSelector />
              </div>

              {/* Cerrar Sesión */}
              {isAuthenticated && (
                <button
                  onClick={handleLogout}
                  style={{
                    width: '100%',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'transparent',
                    color: '#dc3545',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    transition: 'background-color 0.2s ease',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(220, 53, 69, 0.1)'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  {t('navbar.logout')}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
