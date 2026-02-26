import { useState, FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { ApplyResult } from '../../../core/ports/IApiClient';
import EnforcementStatus from './EnforcementStatus';
import { useToast } from '../../../infrastructure/notifications/useToast';

interface IDSP2UploaderProps {
  deviceId: string;
  onApply: (deviceId: string, idsp2Id: string) => Promise<ApplyResult>;
}

/**
 * IDSP2Uploader - Componente para subir y aplicar IDSP2 ID
 */
export default function IDSP2Uploader({ deviceId, onApply }: IDSP2UploaderProps): JSX.Element {
  const { t } = useTranslation();
  const { showTranslated, showApiError } = useToast();
  const [idsp2Id, setIdsp2Id] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ApplyResult | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    
    if (!idsp2Id.trim()) {
      showTranslated('policies.applyIdsp2.error', 'error');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await onApply(deviceId, idsp2Id.trim());
      setResult(response);
    } catch (err) {
      showApiError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* <h2>{t('policies.applyIdsp2.title')}</h2> */}
      <form onSubmit={handleSubmit} style={{ marginTop: '1rem' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="idsp2-id" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
            {t('policies.applyIdsp2.label')}
          </label>
          <input
            id="idsp2-id"
            type="text"
            value={idsp2Id}
            onChange={(e) => setIdsp2Id(e.target.value)}
            placeholder={t('policies.applyIdsp2.placeholder')}
            disabled={loading}
            style={{
              width: '100%',
              maxWidth: '500px',
              padding: '0.5rem',
              fontSize: '1rem',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !idsp2Id.trim()}
          style={{
            padding: '0.75rem 2rem',
            fontSize: '1rem',
            backgroundColor: loading ? '#6c757d' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? t('policies.applyIdsp2.applying') : t('policies.applyIdsp2.button')}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: '1rem' }}>
          <EnforcementStatus 
            status={result.status} 
            message={result.message}
            timestamp={new Date().toISOString()}
          />
        </div>
      )}
    </div>
  );
}

