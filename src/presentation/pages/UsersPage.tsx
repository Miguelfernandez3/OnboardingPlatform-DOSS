/**
 * UsersPage - Página de gestión de usuarios (solo admin)
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile, useUsers, useCreateUser, useUpdateUserRole, useDeleteUser, useActivateUser, useDeactivateUser } from '../hooks';
import { AdminRoute } from '../components/auth';
import { CreateUserModal, ConfirmDeleteModal } from '../components/users';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { UserData } from '../../core/ports';

const ITEMS_PER_PAGE = 10;

export default function UsersPage(): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch users with pagination
  const { users, total, loading, error, refetch } = useUsers(currentPage, ITEMS_PER_PAGE);

  // Mutations
  const createUserMutation = useCreateUser();
  const updateRoleMutation = useUpdateUserRole();
  const deleteUserMutation = useDeleteUser();
  const activateUserMutation = useActivateUser();
  const deactivateUserMutation = useDeactivateUser();

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; user: UserData | null }>({
    isOpen: false,
    user: null,
  });

  // Feedback state
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Calculate pagination info
  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const from = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const to = Math.min(currentPage * ITEMS_PER_PAGE, total);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleCreateUser = async (email: string, password: string, role: string) => {
    try {
      await createUserMutation.mutateAsync({ email, password, role });
      showFeedback('success', t('users.createSuccess'));
      refetch();
    } catch {
      showFeedback('error', t('users.createError'));
      throw new Error(t('users.createError'));
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateRoleMutation.mutateAsync({ id: userId, role: newRole });
      showFeedback('success', t('users.roleUpdateSuccess'));
      refetch();
    } catch (err) {
      const errorCode = getErrorCode(err);
      showFeedback('error', t(`users.errors.${errorCode}`, t('users.roleUpdateError')));
    }
  };

  // Helper function to extract error code from API error
  const getErrorCode = (error: unknown): string => {
    if (error && typeof error === 'object') {
      // Check if it's an axios-style error with response data
      const err = error as { response?: { data?: { code?: string } }; message?: string };
      if (err.response?.data?.code) {
        return err.response.data.code;
      }
      // Check if error message contains a code
      if (err.message) {
        // Try to parse JSON from error message
        try {
          const parsed = JSON.parse(err.message);
          if (parsed.code) return parsed.code;
        } catch {
          // Not JSON, check if it contains known codes
          const knownCodes = ['CANNOT_DEACTIVATE_SELF', 'CANNOT_DELETE_SELF', 'USER_NOT_FOUND', 'EMAIL_EXISTS'];
          for (const code of knownCodes) {
            if (err.message.includes(code)) return code;
          }
        }
      }
    }
    return 'GENERIC';
  };

  const handleToggleActive = async (user: UserData) => {
    try {
      if (user.isActive) {
        await deactivateUserMutation.mutateAsync(user.id);
        showFeedback('success', t('users.deactivateSuccess'));
      } else {
        await activateUserMutation.mutateAsync(user.id);
        showFeedback('success', t('users.activateSuccess'));
      }
      refetch();
    } catch (err) {
      const errorCode = getErrorCode(err);
      const fallbackMsg = user.isActive ? t('users.deactivateError') : t('users.activateError');
      showFeedback('error', t(`users.errors.${errorCode}`, fallbackMsg));
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteModal.user) return;
    try {
      await deleteUserMutation.mutateAsync(deleteModal.user.id);
      showFeedback('success', t('users.deleteSuccess'));
      setDeleteModal({ isOpen: false, user: null });
      refetch();
    } catch (err) {
      const errorCode = getErrorCode(err);
      showFeedback('error', t(`users.errors.${errorCode}`, t('users.deleteError')));
      setDeleteModal({ isOpen: false, user: null });
    }
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return '-';
    }
  };

  if (loading) {
    return (
      <AdminRoute>
        <LoadingSpinner message={t('users.loadingUsers')} />
      </AdminRoute>
    );
  }

  if (error) {
    return (
      <AdminRoute>
        <div style={{ padding: '2rem' }}>
          <div style={{
            padding: '1rem',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            borderRadius: '4px',
            border: '1px solid #f5c6cb'
          }}>
            <strong>{t('common.error')}:</strong> {error}
          </div>
        </div>
      </AdminRoute>
    );
  }

  return (
    <AdminRoute>
      <div style={{ padding: isMobile ? '1rem' : '2rem' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', margin: 0 }}>
            {t('users.title')}
          </h1>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            {t('users.createUser')}
          </button>
        </div>

        {/* Feedback Message */}
        {feedback && (
          <div style={{
            padding: '1rem',
            marginBottom: '1rem',
            borderRadius: '4px',
            backgroundColor: feedback.type === 'success' ? '#d4edda' : '#f8d7da',
            color: feedback.type === 'success' ? '#155724' : '#721c24',
            border: `1px solid ${feedback.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
          }}>
            {feedback.message}
          </div>
        )}

        {users.length === 0 ? (
          <p>{t('users.noUsers')}</p>
        ) : isMobile ? (
          /* Mobile: Card view */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {users.map((user) => (
              <div
                key={user.id}
                style={{
                  padding: '1rem',
                  backgroundColor: '#fff',
                  borderRadius: '8px',
                  border: '1px solid #dee2e6',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{user.email}</h3>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      backgroundColor: user.role === 'admin' ? '#007bff' : '#6c757d',
                      color: 'white',
                      fontSize: '0.75rem',
                      marginTop: '0.25rem',
                      display: 'inline-block'
                    }}>
                      {user.role === 'admin' ? t('users.admin') : t('users.user')}
                    </span>
                  </div>
                  <span style={{
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                    backgroundColor: user.isActive ? '#d4edda' : '#fff3cd',
                    color: user.isActive ? '#155724' : '#856404',
                    fontSize: '0.75rem'
                  }}>
                    {user.isActive ? t('users.active') : t('users.inactive')}
                  </span>
                </div>
                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.75rem' }}>
                  <div><strong>{t('users.lastLogin')}:</strong> {formatDate(user.lastLogin)}</div>
                  <div><strong>{t('users.createdAt')}:</strong> {formatDate(user.createdAt)}</div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <select
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    style={{
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #dee2e6',
                      fontSize: '0.875rem'
                    }}
                  >
                    <option value="user">{t('users.user')}</option>
                    <option value="admin">{t('users.admin')}</option>
                  </select>
                  <button
                    onClick={() => handleToggleActive(user)}
                    style={{
                      padding: '0.5rem 0.75rem',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: user.isActive ? '#ffc107' : '#28a745',
                      color: user.isActive ? '#212529' : 'white',
                      cursor: 'pointer',
                      fontSize: '0.875rem'
                    }}
                  >
                    {user.isActive ? t('users.deactivate') : t('users.activate')}
                  </button>
                  {!user.isActive && (
                    <button
                      onClick={() => setDeleteModal({ isOpen: true, user })}
                      style={{
                        padding: '0.5rem 0.75rem',
                        borderRadius: '4px',
                        border: 'none',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: '0.875rem'
                      }}
                    >
                      {t('users.delete')}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* Desktop: Table view */
          <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              minWidth: '800px'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.email')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.role')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.status')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.lastLogin')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.createdAt')}</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', whiteSpace: 'nowrap' }}>{t('users.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={{ padding: '0.75rem' }}>{user.email}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                        style={{
                          padding: '0.375rem 0.5rem',
                          borderRadius: '4px',
                          border: '1px solid #dee2e6',
                          backgroundColor: user.role === 'admin' ? '#e7f1ff' : 'white',
                          cursor: 'pointer'
                        }}
                      >
                        <option value="user">{t('users.user')}</option>
                        <option value="admin">{t('users.admin')}</option>
                      </select>
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor: user.isActive ? '#d4edda' : '#fff3cd',
                        color: user.isActive ? '#155724' : '#856404',
                        fontSize: '0.875rem'
                      }}>
                        {user.isActive ? t('users.active') : t('users.inactive')}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem' }}>{formatDate(user.lastLogin)}</td>
                    <td style={{ padding: '0.75rem' }}>{formatDate(user.createdAt)}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => handleToggleActive(user)}
                          style={{
                            padding: '0.375rem 0.75rem',
                            borderRadius: '4px',
                            border: 'none',
                            backgroundColor: user.isActive ? '#ffc107' : '#28a745',
                            color: user.isActive ? '#212529' : 'white',
                            cursor: 'pointer',
                            fontSize: '0.875rem'
                          }}
                        >
                          {user.isActive ? t('users.deactivate') : t('users.activate')}
                        </button>
                        {!user.isActive && (
                          <button
                            onClick={() => setDeleteModal({ isOpen: true, user })}
                            style={{
                              padding: '0.375rem 0.75rem',
                              borderRadius: '4px',
                              border: 'none',
                              backgroundColor: '#dc3545',
                              color: 'white',
                              cursor: 'pointer',
                              fontSize: '0.875rem'
                            }}
                          >
                            {t('users.delete')}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > 0 && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '1.5rem',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <span style={{ color: '#666', fontSize: '0.875rem' }}>
                {t('users.pagination.showing', { from, to, total })}
              </span>
              <span style={{ color: '#666', fontSize: '0.875rem', fontWeight: 500 }}>
                {t('users.pagination.page', { page: currentPage, totalPages })}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6',
                  backgroundColor: currentPage === 1 ? '#e9ecef' : 'white',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  color: currentPage === 1 ? '#6c757d' : '#212529'
                }}
              >
                {t('users.pagination.previous')}
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6',
                  backgroundColor: currentPage === totalPages ? '#e9ecef' : 'white',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  color: currentPage === totalPages ? '#6c757d' : '#212529'
                }}
              >
                {t('users.pagination.next')}
              </button>
            </div>
          </div>
        )}

        {/* Modals */}
        <CreateUserModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateUser}
          isLoading={createUserMutation.isPending}
        />

        <ConfirmDeleteModal
          isOpen={deleteModal.isOpen}
          userEmail={deleteModal.user?.email || ''}
          onClose={() => setDeleteModal({ isOpen: false, user: null })}
          onConfirm={handleDeleteUser}
          isLoading={deleteUserMutation.isPending}
        />
      </div>
    </AdminRoute>
  );
}
