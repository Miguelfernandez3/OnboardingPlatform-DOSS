import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { usePolicies, useDevice, useIsMobile } from '../hooks';
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
  const isMobile = useIsMobile();
  
  // Obtener información del dispositivo
  const { 
    device,
    loading: deviceLoading
  } = useDevice(id);

  const {
    applyPolicy,
    applyIDSP2,
    loading: policiesLoading
  } = usePolicies(id);

  const handleApplyPolicy = async (msplXml: string, name?: string): Promise<void> => {
    try {
      await applyPolicy(msplXml, name);
      alert(t('policies.createEdit.success'));
      navigate(`/devices/${id}#policies`);
    } catch (err) {
      alert(`${t('policies.createEdit.error')}: ${(err as Error).message}`);
    }
  };

  const handleApplyIDSP2 = async (_deviceId: string, idsp2Id: string) => {
    try {
      const result = await applyIDSP2(idsp2Id);
      alert(t('policies.createEdit.success'));
      navigate(`/devices/${id}#policies`);
      return result;
    } catch (err) {
      alert(`${t('policies.createEdit.error')}: ${(err as Error).message}`);
      throw err;
    }
  };

  const handleCancel = (): void => {
    navigate(`/devices/${id}#policies`);
  };

  if (policiesLoading || deviceLoading) {
    return <LoadingSpinner message={t('common.loading')} />;
  }

  return (
    <div style={{ padding: isMobile ? '1rem' : '2rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between',
        alignItems: isMobile ? 'stretch' : 'center',
        gap: isMobile ? '1rem' : '0',
        marginBottom: isMobile ? '1.5rem' : '2rem'
      }}>
        <h1 style={{ margin: 0, fontSize: isMobile ? '1.25rem' : '2rem' }}>
          {t('policies.createPage.title', { deviceName: device?.name || id })}
        </h1>
        <button
          onClick={handleCancel}
          style={{
            padding: isMobile ? '0.75rem 1rem' : '0.5rem 1rem',
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
        marginBottom: isMobile ? '2rem' : '3rem',
        padding: isMobile ? '1rem' : '1.5rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: isMobile ? '1.1rem' : '1.5rem' }}>
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
        marginBottom: isMobile ? '2rem' : '3rem'
      }} />

      {/* MSPL Editor Section */}
      <div style={{
        padding: isMobile ? '1rem' : '1.5rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: isMobile ? '1.1rem' : '1.5rem' }}>
          {t('policies.createPage.msplSection')}
        </h2>
        <MSPLEditor
          onApply={handleApplyPolicy}
        />
      </div>

      {/* Footer Actions */}
      <div style={{
        display: 'flex',
        justifyContent: isMobile ? 'stretch' : 'flex-end',
        gap: '1rem',
        marginTop: isMobile ? '1.5rem' : '2rem',
        paddingTop: isMobile ? '1.5rem' : '2rem',
        borderTop: '2px solid #dee2e6'
      }}>
        <button
          onClick={handleCancel}
          style={{
            flex: isMobile ? 1 : 'none',
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


