import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';

interface CreateUserModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (email: string, password: string, role: string) => Promise<void>;
    isLoading?: boolean;
}

/**
 * CreateUserModal - Modal para crear un nuevo usuario
 */
export default function CreateUserModal({
    isOpen,
    onClose,
    onSubmit,
    isLoading = false,
}: CreateUserModalProps): JSX.Element | null {
    const { t } = useTranslation();
    const isMobile = useIsMobile();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [role, setRole] = useState('user');
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const validateEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validations
        if (!email.trim()) {
            setError(t('users.createModal.emailRequired'));
            return;
        }
        if (!validateEmail(email)) {
            setError(t('users.createModal.invalidEmail'));
            return;
        }
        if (password.length < 8) {
            setError(t('users.createModal.passwordTooShort'));
            return;
        }
        if (password !== confirmPassword) {
            setError(t('users.createModal.passwordMismatch'));
            return;
        }

        try {
            await onSubmit(email, password, role);
            // Reset form on success
            setEmail('');
            setPassword('');
            setConfirmPassword('');
            setRole('user');
            setError(null);
            onClose();
        } catch (err) {
            setError((err as Error).message || t('users.createError'));
        }
    };

    const handleClose = () => {
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        setRole('user');
        setError(null);
        onClose();
    };

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                padding: isMobile ? '1rem' : '0',
            }}
            onClick={handleClose}
        >
            <div
                style={{
                    backgroundColor: 'white',
                    borderRadius: '8px',
                    padding: isMobile ? '1.5rem' : '2rem',
                    width: '100%',
                    maxWidth: '450px',
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <h2 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: isMobile ? '1.25rem' : '1.5rem' }}>
                    {t('users.createModal.title')}
                </h2>

                <form onSubmit={handleSubmit}>
                    {/* Email */}
                    <div style={{ marginBottom: '1rem' }}>
                        <label
                            htmlFor="email"
                            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}
                        >
                            {t('users.createModal.email')}
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder={t('users.createModal.emailPlaceholder')}
                            disabled={isLoading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '4px',
                                border: '1px solid #dee2e6',
                                fontSize: '1rem',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>

                    {/* Password */}
                    <div style={{ marginBottom: '1rem' }}>
                        <label
                            htmlFor="password"
                            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}
                        >
                            {t('users.createModal.password')}
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder={t('users.createModal.passwordPlaceholder')}
                            disabled={isLoading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '4px',
                                border: '1px solid #dee2e6',
                                fontSize: '1rem',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>

                    {/* Confirm Password */}
                    <div style={{ marginBottom: '1rem' }}>
                        <label
                            htmlFor="confirmPassword"
                            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}
                        >
                            {t('users.createModal.confirmPassword')}
                        </label>
                        <input
                            id="confirmPassword"
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder={t('users.createModal.confirmPasswordPlaceholder')}
                            disabled={isLoading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '4px',
                                border: '1px solid #dee2e6',
                                fontSize: '1rem',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>

                    {/* Role */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label
                            htmlFor="role"
                            style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}
                        >
                            {t('users.createModal.role')}
                        </label>
                        <select
                            id="role"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                            disabled={isLoading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '4px',
                                border: '1px solid #dee2e6',
                                fontSize: '1rem',
                                backgroundColor: 'white',
                                boxSizing: 'border-box',
                            }}
                        >
                            <option value="user">{t('users.user')}</option>
                            <option value="admin">{t('users.admin')}</option>
                        </select>
                    </div>

                    {/* Error message */}
                    {error && (
                        <div
                            style={{
                                padding: '0.75rem',
                                backgroundColor: '#f8d7da',
                                color: '#721c24',
                                borderRadius: '4px',
                                marginBottom: '1rem',
                                fontSize: '0.875rem',
                            }}
                        >
                            {error}
                        </div>
                    )}

                    {/* Buttons */}
                    <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                        <button
                            type="button"
                            onClick={handleClose}
                            disabled={isLoading}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '4px',
                                border: '1px solid #dee2e6',
                                backgroundColor: 'white',
                                cursor: 'pointer',
                                fontSize: '1rem',
                            }}
                        >
                            {t('users.createModal.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '4px',
                                border: 'none',
                                backgroundColor: '#007bff',
                                color: 'white',
                                cursor: isLoading ? 'not-allowed' : 'pointer',
                                fontSize: '1rem',
                                opacity: isLoading ? 0.7 : 1,
                            }}
                        >
                            {isLoading ? t('users.createModal.creating') : t('users.createModal.create')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
