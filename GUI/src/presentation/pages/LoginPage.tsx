/**
 * LoginPage - Página de inicio de sesión
 */
import { useState, FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { useIsMobile } from '../hooks';
import { useToast } from '../../infrastructure/notifications/useToast';

export default function LoginPage(): JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();
  const isMobile = useIsMobile();
  const { showApiError } = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Redirigir si ya está autenticado (usando useEffect para evitar warning)
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/devices', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Si está autenticado, no mostrar el formulario
  if (isAuthenticated) {
    return <></>;
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      // La redirección se hará automáticamente por el useEffect cuando isAuthenticated cambie
    } catch (err) {
      showApiError(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f5f5f5',
      padding: isMobile ? '1rem' : '2rem'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        backgroundColor: '#fff',
        padding: isMobile ? '1.5rem' : '2rem',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{
          fontSize: isMobile ? '1.5rem' : '2rem',
          marginBottom: '1.5rem',
          textAlign: 'center',
          color: '#343a40'
        }}>
          {t('auth.login')}
        </h1>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="email" style={{
              display: 'block',
              marginBottom: '0.5rem',
              fontWeight: '500',
              color: '#343a40'
            }}>
              {t('auth.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                fontSize: '1rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label htmlFor="password" style={{
              display: 'block',
              marginBottom: '0.5rem',
              fontWeight: '500',
              color: '#343a40'
            }}>
              {t('auth.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                fontSize: '1rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            aria-busy={isLoading}
            style={{
              width: '100%',
              height: '48px',
              padding: '0 0.75rem',
              position: 'relative',
              boxSizing: 'border-box',
              backgroundColor: isLoading ? '#0056b3' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              fontWeight: '500',
              lineHeight: 1,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              overflow: 'hidden',
            }}
          >
            <span style={{ opacity: isLoading ? 0 : 1 }}>
              {t('auth.submit')}
            </span>
            {isLoading && (
              <>
                <span
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  aria-hidden
                >
                  <span className="loading-spinner-ring loading-spinner-ring--sm loading-spinner-ring--light" />
                </span>
                <span className="visually-hidden">{t('auth.submitting')}</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
