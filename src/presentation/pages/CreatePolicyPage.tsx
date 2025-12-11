import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { usePolicies } from '../hooks/usePolicies';
import IDSP2Uploader from '../components/policies/IDSP2Uploader';
import MSPLEditor from '../components/mspl/MSPLEditor';
import LoadingSpinner from '../components/common/LoadingSpinner';

/**
 * CreatePolicyPage - Página dedicada para crear nuevas políticas
 */
export default function CreatePolicyPage(): JSX.Element {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    applyPolicy,
    applyIDSP2,
    loading: policiesLoading
  } = usePolicies(id);

  const handleApplyPolicy = async (msplXml: string): Promise<void> => {
    try {
      await applyPolicy(msplXml);
      alert(t('policies.createEdit.success'));
      navigate(`/devices/${id}`);
    } catch (err) {
      alert(`${t('policies.createEdit.error')}: ${(err as Error).message}`);
    }
  };

  const handleApplyIDSP2 = async (deviceId: string, idsp2Id: string) => {
    try {
      const result = await applyIDSP2(idsp2Id);
      alert(t('policies.createEdit.success'));
      navigate(`/devices/${id}`);
      return result;
    } catch (err) {
      alert(`${t('policies.createEdit.error')}: ${(err as Error).message}`);
      throw err;
    }
  };

  const handleCancel = (): void => {
    navigate(`/devices/${id}`);
  };

  if (policiesLoading) {
    return <LoadingSpinner message={t('common.loading')} />;
  }

  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <h1>{t('policies.createPage.title')}</h1>
        <button
          onClick={handleCancel}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          {t('policies.createPage.back')}
        </button>
      </div>

      {/* IDSP2 Section */}
      <div style={{
        marginBottom: '3rem',
        padding: '1.5rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>
          {t('policies.createPage.idsp2Section')}
        </h2>
        <IDSP2Uploader 
          deviceId={id || ''} 
          onApply={handleApplyIDSP2}
        />
      </div>

      {/* Divider */}
      <div style={{
        height: '2px',
        backgroundColor: '#dee2e6',
        marginBottom: '3rem'
      }} />

      {/* MSPL Editor Section */}
      <div style={{
        padding: '1.5rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>
          {t('policies.createPage.msplSection')}
        </h2>
        <MSPLEditor
          onApply={handleApplyPolicy}
        />
      </div>

      {/* Footer Actions */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '1rem',
        marginTop: '2rem',
        paddingTop: '2rem',
        borderTop: '2px solid #dee2e6'
      }}>
        <button
          onClick={handleCancel}
          style={{
            padding: '0.75rem 2rem',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          {t('policies.createPage.cancel')}
        </button>
      </div>
    </div>
  );
}
