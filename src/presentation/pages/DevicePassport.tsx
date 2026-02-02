import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../../config';
import { Passport } from '../../core/domain/entities/Passport';
import JsonViewer from '../components/common/JsonViewer';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useToast } from '../../infrastructure/notifications/useToast';

/**
 * DevicePassport - Página que muestra el pasaporte digital del dispositivo
 */
export default function DevicePassport(): JSX.Element {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { showApiError } = useToast();
  const [passport, setPassport] = useState<Passport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchPassport = async (): Promise<void> => {
      if (!id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const data = await apiClient.getDevicePassport(id);
        setPassport(data);
      } catch (err) {
        showApiError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPassport();
  }, [id, showApiError]);

  if (loading) {
    return <LoadingSpinner message={t('device.passport.loading')} />;
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

