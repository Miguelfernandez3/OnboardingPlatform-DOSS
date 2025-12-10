import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';
import JsonViewer from '../components/common/JsonViewer';
import LoadingSpinner from '../components/common/LoadingSpinner';

/**
 * DevicePassport - Página que muestra el pasaporte digital del dispositivo
 */
export default function DevicePassport(): JSX.Element {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const [passport, setPassport] = useState<Passport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPassport = async (): Promise<void> => {
      if (!id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await apiClient.getDevicePassport(id);
        setPassport(data);
      } catch (err) {
        setError((err as Error).message || t('device.passport.error'));
      } finally {
        setLoading(false);
      }
    };

    fetchPassport();
  }, [id, t]);

  if (loading) {
    return <LoadingSpinner message={t('device.passport.loading')} />;
  }

  if (error) {
    return (
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
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>{t('device.passport.title')} - {t('devices.title')} {id}</h1>
      {passport ? (
        <JsonViewer data={passport.toJSON()} title={t('device.passport.title')} />
      ) : (
        <p>{t('device.passport.noData')}</p>
      )}
    </div>
  );
}

