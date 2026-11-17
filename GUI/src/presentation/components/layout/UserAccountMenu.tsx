import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnreadNotificationsCount } from '../../hooks/useNotifications';

function emailToAvatarLabel(email: string): string {
  const local = (email.split('@')[0] || email).replace(/[^a-zA-Z0-9]/g, '');
  if (!local) return '?';
  const raw = local.slice(0, 3);
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}

function CountBubble({
  count,
  style: extra
}: {
  count: number;
  style?: CSSProperties;
}): JSX.Element | null {
  if (count < 1) return null;
  const label = count > 99 ? '99+' : String(count);
  const base: CSSProperties = {
    minWidth: 18,
    height: 18,
    padding: '0 5px',
    borderRadius: 999,
    backgroundColor: '#dc3545',
    color: 'white',
    fontSize: 11,
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    lineHeight: 1,
    flexShrink: 0
  };
  return <span style={{ ...base, ...extra }}>{label}</span>;
}

export interface UserAccountMenuProps {
  userEmail: string;
  isAdmin: boolean;
  onLogout: () => void;
}

/**
 * Avatar con iniciales, contador de no leídas (TanStack Query) y menú desplegable.
 */
export default function UserAccountMenu({ userEmail, isAdmin, onLogout }: UserAccountMenuProps): JSX.Element {
  const { t } = useTranslation();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data: unreadTotal = 0 } = useUnreadNotificationsCount(true);
  const unread = typeof unreadTotal === 'number' ? unreadTotal : 0;

  const isActive = (path: string): boolean => location.pathname === path;
  const label = emailToAvatarLabel(userEmail);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const linkStyle = (active: boolean): CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '0.5rem',
    padding: '0.75rem 1rem',
    color: active ? '#ffc107' : 'rgba(255, 255, 255, 0.9)',
    textDecoration: 'none',
    fontSize: '0.875rem',
    fontWeight: active ? 600 : 400
  });

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        aria-label={t('navbar.userMenu')}
        aria-haspopup="true"
        onClick={() => setOpen(v => !v)}
        style={{
          position: 'relative',
          width: 44,
          height: 44,
          borderRadius: '50%',
          border: '2px solid rgba(255,255,255,0.35)',
          background: 'linear-gradient(145deg, #5b21b6 0%, #4c1d95 100%)',
          color: '#fff',
          cursor: 'pointer',
          fontSize: '0.95rem',
          fontWeight: 700,
          letterSpacing: '-0.02em',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.25)'
        }}
      >
        {label}
        <CountBubble
          count={unread}
          style={{
            position: 'absolute',
            bottom: -2.5,
            right: -2.5,
            border: '2px solid #343a40',
            minWidth: 20,
            height: 20,
            fontSize: 10
          }}
        />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 10px)',
            right: 0,
            backgroundColor: '#343a40',
            borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
            minWidth: 240,
            overflow: 'hidden',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            zIndex: 1000
          }}
        >
          <div
            style={{
              padding: '0.85rem 1rem',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              backgroundColor: 'rgba(255, 255, 255, 0.05)'
            }}
          >
            <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
              {t('navbar.signedInAs')}
            </div>
            <div style={{ color: 'white', fontSize: '0.875rem', wordBreak: 'break-all' }}>{userEmail}</div>
          </div>

          <div style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <Link to="/devices" onClick={() => setOpen(false)} style={linkStyle(isActive('/devices'))}>
              <span>{t('navbar.devices')}</span>
            </Link>
            <Link to="/settings" onClick={() => setOpen(false)} style={linkStyle(isActive('/settings'))}>
              <span>{t('navbar.settings')}</span>
            </Link>
            <Link
              to="/notifications"
              onClick={() => setOpen(false)}
              style={linkStyle(location.pathname.startsWith('/notifications'))}
            >
              <span>{t('navbar.notifications')}</span>
              <CountBubble count={unread} />
            </Link>
            {isAdmin && (
              <Link to="/users" onClick={() => setOpen(false)} style={linkStyle(isActive('/users'))}>
                <span>{t('navbar.users')}</span>
              </Link>
            )}
            {isAdmin && (
              <Link
                to="/admin/enforcement"
                onClick={() => setOpen(false)}
                style={linkStyle(isActive('/admin/enforcement'))}
              >
                <span>{t('navbar.enforcement')}</span>
              </Link>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
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
              gap: '0.5rem'
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            {t('navbar.logout')}
          </button>
        </div>
      )}
    </div>
  );
}
