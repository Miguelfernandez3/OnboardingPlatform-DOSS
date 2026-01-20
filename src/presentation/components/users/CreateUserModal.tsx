import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';

interface CreateUserModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (email: string, password: string, role: string) => Promise<void>;
    isLoading?: boolean;
}

interface FieldErrors {
    email: string | null;
    password: string | null;
    confirmPassword: string | null;
}

/**
 * CreateUserModal - Modal para crear un nuevo usuario
 * Con validación en tiempo real (debounced)
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
    const [submitError, setSubmitError] = useState<string | null>(null);

    // Field-specific errors for real-time validation
    const [fieldErrors, setFieldErrors] = useState<FieldErrors>({
        email: null,
        password: null,
        confirmPassword: null,
    });

    // Track which fields have been touched (to avoid showing errors on fresh form)
    const [touched, setTouched] = useState({
        email: false,
        password: false,
        confirmPassword: false,
    });

    // Debounce timers
    const emailTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const passwordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const confirmPasswordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const DEBOUNCE_MS = 800;

    const validateEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    // Debounced email validation
    useEffect(() => {
        if (!touched.email) return;

        if (emailTimerRef.current) {
            clearTimeout(emailTimerRef.current);
        }

        emailTimerRef.current = setTimeout(() => {
            if (!email.trim()) {
                setFieldErrors(prev => ({ ...prev, email: t('users.createModal.emailRequired') }));
            } else if (!validateEmail(email)) {
                setFieldErrors(prev => ({ ...prev, email: t('users.createModal.invalidEmail') }));
            } else {
                setFieldErrors(prev => ({ ...prev, email: null }));
            }
        }, DEBOUNCE_MS);

        return () => {
            if (emailTimerRef.current) clearTimeout(emailTimerRef.current);
        };
    }, [email, touched.email, t]);

    // Debounced password validation
    useEffect(() => {
        if (!touched.password) return;

        if (passwordTimerRef.current) {
            clearTimeout(passwordTimerRef.current);
        }

        passwordTimerRef.current = setTimeout(() => {
            if (password.length > 0 && password.length < 8) {
                setFieldErrors(prev => ({ ...prev, password: t('users.createModal.passwordTooShort') }));
            } else {
                setFieldErrors(prev => ({ ...prev, password: null }));
            }

            // Also revalidate confirm password when password changes
            if (touched.confirmPassword && confirmPassword && password !== confirmPassword) {
                setFieldErrors(prev => ({ ...prev, confirmPassword: t('users.createModal.passwordMismatch') }));
            } else if (touched.confirmPassword && confirmPassword) {
                setFieldErrors(prev => ({ ...prev, confirmPassword: null }));
            }
        }, DEBOUNCE_MS);

        return () => {
            if (passwordTimerRef.current) clearTimeout(passwordTimerRef.current);
        };
    }, [password, touched.password, confirmPassword, touched.confirmPassword, t]);

    // Debounced confirm password validation
    useEffect(() => {
        if (!touched.confirmPassword) return;

        if (confirmPasswordTimerRef.current) {
            clearTimeout(confirmPasswordTimerRef.current);
        }

        confirmPasswordTimerRef.current = setTimeout(() => {
            if (confirmPassword && password !== confirmPassword) {
                setFieldErrors(prev => ({ ...prev, confirmPassword: t('users.createModal.passwordMismatch') }));
            } else {
                setFieldErrors(prev => ({ ...prev, confirmPassword: null }));
            }
        }, DEBOUNCE_MS);

        return () => {
            if (confirmPasswordTimerRef.current) clearTimeout(confirmPasswordTimerRef.current);
        };
    }, [confirmPassword, password, touched.confirmPassword, t]);

    // Cleanup timers on unmount
    useEffect(() => {
        return () => {
            if (emailTimerRef.current) clearTimeout(emailTimerRef.current);
            if (passwordTimerRef.current) clearTimeout(passwordTimerRef.current);
            if (confirmPasswordTimerRef.current) clearTimeout(confirmPasswordTimerRef.current);
        };
    }, []);

    if (!isOpen) return null;

    const getInputStyle = (fieldName: keyof FieldErrors) => {
        const baseStyle = {
            width: '100%',
            padding: '0.75rem',
            borderRadius: '4px',
            fontSize: '1rem',
            boxSizing: 'border-box' as const,
            transition: 'border-color 0.2s ease',
        };

        if (fieldErrors[fieldName]) {
            return { ...baseStyle, border: '2px solid #dc3545' };
        }

        // Show green border only if field is touched and valid
        const fieldValue = fieldName === 'email' ? email : fieldName === 'password' ? password : confirmPassword;
        if (touched[fieldName] && fieldValue && !fieldErrors[fieldName]) {
            return { ...baseStyle, border: '2px solid #28a745' };
        }

        return { ...baseStyle, border: '1px solid #dee2e6' };
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitError(null);

        // Final validation before submit
        if (!email.trim()) {
            setSubmitError(t('users.createModal.emailRequired'));
            return;
        }
        if (!validateEmail(email)) {
            setSubmitError(t('users.createModal.invalidEmail'));
            return;
        }
        if (password.length < 8) {
            setSubmitError(t('users.createModal.passwordTooShort'));
            return;
        }
        if (password !== confirmPassword) {
            setSubmitError(t('users.createModal.passwordMismatch'));
            return;
        }

        try {
            await onSubmit(email, password, role);
            // Reset form on success
            resetForm();
            onClose();
        } catch (err) {
            setSubmitError((err as Error).message || t('users.createError'));
        }
    };

    const resetForm = () => {
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        setRole('user');
        setSubmitError(null);
        setFieldErrors({ email: null, password: null, confirmPassword: null });
        setTouched({ email: false, password: false, confirmPassword: false });
    };

    const handleClose = () => {
        resetForm();
        onClose();
    };

    const hasErrors = Object.values(fieldErrors).some(e => e !== null);
    const isFormValid = email && password && confirmPassword && password === confirmPassword && password.length >= 8 && validateEmail(email);

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
            onMouseDown={handleClose}
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
                onMouseDown={(e) => e.stopPropagation()}
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
                            onChange={(e) => {
                                setEmail(e.target.value);
                                if (!touched.email) setTouched(prev => ({ ...prev, email: true }));
                            }}
                            placeholder={t('users.createModal.emailPlaceholder')}
                            disabled={isLoading}
                            style={getInputStyle('email')}
                        />
                        {fieldErrors.email && (
                            <div style={{ color: '#dc3545', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                {fieldErrors.email}
                            </div>
                        )}
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
                            onChange={(e) => {
                                setPassword(e.target.value);
                                if (!touched.password) setTouched(prev => ({ ...prev, password: true }));
                            }}
                            placeholder={t('users.createModal.passwordPlaceholder')}
                            disabled={isLoading}
                            style={getInputStyle('password')}
                        />
                        {fieldErrors.password && (
                            <div style={{ color: '#dc3545', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                {fieldErrors.password}
                            </div>
                        )}
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
                            onChange={(e) => {
                                setConfirmPassword(e.target.value);
                                if (!touched.confirmPassword) setTouched(prev => ({ ...prev, confirmPassword: true }));
                            }}
                            placeholder={t('users.createModal.confirmPasswordPlaceholder')}
                            disabled={isLoading}
                            style={getInputStyle('confirmPassword')}
                        />
                        {fieldErrors.confirmPassword && (
                            <div style={{ color: '#dc3545', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                {fieldErrors.confirmPassword}
                            </div>
                        )}
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

                    {/* Submit error message */}
                    {submitError && (
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
                            {submitError}
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
                            disabled={isLoading || hasErrors || !isFormValid}
                            style={{
                                padding: '0.75rem 1.5rem',
                                borderRadius: '4px',
                                border: 'none',
                                backgroundColor: (isLoading || hasErrors || !isFormValid) ? '#6c757d' : '#007bff',
                                color: 'white',
                                cursor: (isLoading || hasErrors || !isFormValid) ? 'not-allowed' : 'pointer',
                                fontSize: '1rem',
                                opacity: (isLoading || hasErrors || !isFormValid) ? 0.7 : 1,
                                transition: 'background-color 0.2s ease, opacity 0.2s ease',
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
