import { useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useIsMobile, useNotificationsList } from '../hooks';
import { useToast } from '../../infrastructure/notifications/useToast';
import type { AppNotification } from '../../infrastructure/services/notificationService';

export interface NotificationsPageProps {
  /** `unread`: solo pendientes; `read`: archivo de leídas */
  readFilter?: 'unread' | 'read';
}

function stripHtml(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}

function parseNotificationContent(message: string): { headline: string; body: string } {
  const plain = stripHtml(message);
  const sep = plain.indexOf('\n\n');
  if (sep > 0) {
    const headline = plain.slice(0, sep).replace(/^⚠️\s*/u, '').trim();
    const body = plain.slice(sep).replace(/^\n+/, '').trim();
    if (headline.length > 0 && headline.length < 160 && body.length > 0) {
      return { headline, body };
    }
  }
  return { headline: '', body: plain };
}

function formatNotificationDate(iso: string | null): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

function notificationTypeLabel(type: string, t: (k: string) => string): string {
  if (type === 'missing_mitigation_fields') return t('notifications.typeMitigation');
  if (type === 'missing_enforcement_context') return t('notifications.typePolicy');
  if (type === 'feam_unavailable') return t('notifications.typeFeam');
  return t('notifications.typeOther');
}

const linkMuted: CSSProperties = {
  fontSize: '0.9rem',
  fontWeight: 600,
  color: '#5b21b6',
  textDecoration: 'none',
  borderBottom: '1px solid rgba(91, 33, 182, 0.35)'
};

const btnOutline: CSSProperties = {
  fontSize: '0.875rem',
  cursor: 'pointer',
  padding: '0.45rem 0.9rem',
  borderRadius: 8,
  border: '1px solid #ced4da',
  background: '#fff',
  fontWeight: 600,
  color: '#343a40'
};

export default function NotificationsPage({ readFilter = 'unread' }: NotificationsPageProps): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { showTranslated } = useToast();
  const [page, setPage] = useState(1);

  const {
    notifications,
    totalPages,
    isLoading,
    isFetching,
    isError,
    error,
    markReadMutation,
    markAllReadMutation
  } = useNotificationsList(readFilter, page);

  const markingAll = markAllReadMutation.isPending;
  const errorMessage = isError ? ((error as Error)?.message ?? String(error)) : null;

  const markAllRead = (): void => {
    if (readFilter !== 'unread' || notifications.length === 0 || markingAll) return;
    markAllReadMutation.mutate(undefined, {
      onSuccess: (data: { updated: number }) => {
        if (data.updated === 0) {
          showTranslated('notifications.markAllReadNothing', 'info');
        } else {
          showTranslated('notifications.allMarkedRead', 'success');
        }
        if (page > 1) {
          setPage(1);
        }
      },
      onError: () => {
        showTranslated('notifications.markAllReadError', 'error');
      }
    });
  };

  if (isLoading && notifications.length === 0 && !isError) {
    return <LoadingSpinner message={t('notifications.loading')} />;
  }

  if (isError && notifications.length === 0) {
    return (
      <div style={{ padding: '2rem', color: '#721c24' }}>
        <strong>{t('common.error')}:</strong> {errorMessage}
      </div>
    );
  }

  const emptyKey = readFilter === 'read' ? 'notifications.emptyRead' : 'notifications.emptyUnread';

  return (
    <div style={{ padding: isMobile ? '1rem' : '2rem', maxWidth: '960px' }}>
      <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', marginBottom: '0.35rem' }}>
        {readFilter === 'read' ? t('notifications.readArchiveTitle') : t('notifications.title')}
      </h1>

      <div
        style={{
          marginTop: '0.75rem',
          marginBottom: '1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '0.75rem',
          justifyContent: 'space-between'
        }}
      >
        {readFilter === 'unread' ? (
          <>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem', alignItems: 'center' }}>
              <button
                type="button"
                disabled={markingAll || notifications.length === 0}
                onClick={() => markAllRead()}
                style={{
                  ...btnOutline,
                  opacity: markingAll || notifications.length === 0 ? 0.55 : 1,
                  cursor: markingAll || notifications.length === 0 ? 'not-allowed' : 'pointer'
                }}
              >
                {markingAll ? t('notifications.markingAll') : t('notifications.markAllRead')}
              </button>
            </div>
            <Link to="/notifications/read" style={linkMuted}>
              {t('notifications.viewReadLink')} →
            </Link>
          </>
        ) : (
          <Link to="/notifications" style={{ ...linkMuted, fontWeight: 600 }}>
            ← {t('notifications.backToUnread')}
          </Link>
        )}
      </div>

      <section>
        {notifications.length === 0 ? (
          <p style={{ color: '#6c757d', marginTop: '0.5rem' }}>{t(emptyKey)}</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {notifications.map((n: AppNotification) => {
              const { headline, body } = parseNotificationContent(n.message);
              const isUnreadList = readFilter === 'unread';
              const unread = isUnreadList;
              return (
                <li
                  key={n.id}
                  style={{
                    border: '1px solid #e9ecef',
                    borderLeftWidth: unread ? 4 : 1,
                    borderLeftStyle: 'solid',
                    borderLeftColor: unread ? '#f59e0b' : '#e9ecef',
                    borderRadius: 12,
                    marginBottom: '0.75rem',
                    overflow: 'hidden',
                    backgroundColor: unread ? '#fffbeb' : '#fafbfc',
                    boxShadow: unread ? '0 2px 8px rgba(245, 158, 11, 0.12)' : '0 1px 3px rgba(0,0,0,0.05)'
                  }}
                >
                  <div
                    style={{
                      padding: '0.75rem 1rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      gap: '0.75rem',
                      flexWrap: 'wrap',
                      borderBottom: '1px solid rgba(0,0,0,0.06)',
                      backgroundColor: unread ? 'rgba(255,255,255,0.5)' : '#f3f4f6'
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.8rem', color: '#6c757d', lineHeight: 1.4 }}>
                        <time dateTime={n.createdAt ?? undefined}>{formatNotificationDate(n.createdAt)}</time>
                        {readFilter === 'read' && n.readAt && (
                          <>
                            {' · '}
                            <span>{t('notifications.readAt', { when: formatNotificationDate(n.readAt) })}</span>
                          </>
                        )}
                        {' · '}
                        <span style={{ textTransform: 'capitalize' }}>{n.status}</span>
                        {' · '}
                        <span style={{ color: '#495057', fontWeight: 500 }}>
                          {notificationTypeLabel(n.notificationType, t)}
                        </span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                      {n.deviceId && (
                        <Link
                          to={`/devices/${n.deviceId}`}
                          style={{
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            color: '#5b21b6',
                            textDecoration: 'none',
                            borderBottom: '1px solid rgba(91, 33, 182, 0.35)'
                          }}
                        >
                          {t('notifications.openDevice')}
                        </Link>
                      )}
                      {unread && (
                        <button
                          type="button"
                          disabled={markReadMutation.isPending}
                          onClick={() => markReadMutation.mutate(n.id)}
                          style={{
                            fontSize: '0.8rem',
                            cursor: markReadMutation.isPending ? 'wait' : 'pointer',
                            padding: '0.35rem 0.75rem',
                            borderRadius: 6,
                            border: '1px solid #ced4da',
                            background: '#fff',
                            fontWeight: 500
                          }}
                        >
                          {t('notifications.markRead')}
                        </button>
                      )}
                    </div>
                  </div>
                  <div style={{ padding: '1rem 1rem 1.1rem', backgroundColor: readFilter === 'read' ? '#fff' : undefined }}>
                    {headline ? (
                      <>
                        <h3
                          style={{
                            margin: '0 0 0.6rem',
                            fontSize: '1.05rem',
                            fontWeight: 700,
                            color: '#111827',
                            lineHeight: 1.35
                          }}
                        >
                          {headline}
                        </h3>
                        <div
                          style={{
                            fontSize: '0.95rem',
                            color: '#374151',
                            lineHeight: 1.6,
                            whiteSpace: 'pre-wrap'
                          }}
                        >
                          {body}
                        </div>
                      </>
                    ) : (
                      <div
                        style={{
                          fontSize: '0.95rem',
                          color: '#374151',
                          lineHeight: 1.6,
                          whiteSpace: 'pre-wrap'
                        }}
                      >
                        {body}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {totalPages > 1 && (
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              disabled={page <= 1 || isFetching}
              onClick={() => setPage((p: number) => Math.max(1, p - 1))}
            >
              {t('notifications.prev')}
            </button>
            <span>
              {page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages || isFetching}
              onClick={() => setPage((p: number) => p + 1)}
            >
              {t('notifications.next')}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
