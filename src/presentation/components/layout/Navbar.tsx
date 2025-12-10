import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSelector from '../common/LanguageSelector';

/**
 * Navbar - Componente de navegación
 */
export default function Navbar(): JSX.Element {
  const location = useLocation();
  const { t } = useTranslation();

  const isActive = (path: string): boolean => location.pathname === path;

  return (
    <nav style={{
      backgroundColor: '#343a40',
      padding: '1rem 2rem',
      marginBottom: '2rem'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '2rem'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2rem'
        }}>
          <Link 
            to="/" 
            style={{
              color: 'white',
              textDecoration: 'none',
              fontSize: '1.5rem',
              fontWeight: 'bold'
            }}
          >
            {t('navbar.title')}
          </Link>
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
          </div>
        </div>
        <LanguageSelector />
      </div>
    </nav>
  );
}

