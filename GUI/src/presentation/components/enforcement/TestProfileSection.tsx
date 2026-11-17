import { useTranslation } from 'react-i18next';
import { EnforcementTestResponse } from '../../../core/ports';
import * as s from './styles';

interface Props {
  profileOptions: { value: string; label: string }[];
  testProfileId: string;
  setTestProfileId: (v: string) => void;
  testRunMode: 'preview' | 'execute';
  setTestRunMode: (v: 'preview' | 'execute') => void;
  testContextText: string;
  setTestContextText: (v: string) => void;
  testResult: EnforcementTestResponse | null;
  onRunTest: () => Promise<{ error?: string }>;
  onSuccess: (msg: string) => void;
  onError: (err: unknown) => void;
  onValidationError: (msg: string) => void;
}

export default function TestProfileSection({
  profileOptions, testProfileId, setTestProfileId,
  testRunMode, setTestRunMode, testContextText, setTestContextText,
  testResult, onRunTest, onSuccess, onError, onValidationError
}: Props): JSX.Element {
  const { t } = useTranslation();

  const handleRun = async () => {
    try {
      const result = await onRunTest();
      if (result.error === 'profileRequired') {
        onValidationError(t('enforcementAdmin.test.profileRequired'));
        return;
      }
      if (result.error === 'invalidJson') {
        onValidationError(t('enforcementAdmin.test.invalidJson'));
        return;
      }
      onSuccess(t('enforcementAdmin.test.success'));
    } catch (err) {
      onError(err);
    }
  };

  return (
    <div style={s.card}>
      <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.25rem' }}>
        {t('enforcementAdmin.test.title')}
      </h2>

      <div style={s.formGrid}>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.test.selectProfile')}</div>
          <select style={s.select} value={testProfileId} onChange={e => setTestProfileId(e.target.value)}>
            <option value="">{t('enforcementAdmin.test.selectProfile')}</option>
            {profileOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <div style={s.formLabel}>{t('enforcementAdmin.test.runMode')}</div>
          <select style={s.select} value={testRunMode} onChange={e => setTestRunMode(e.target.value as 'preview' | 'execute')}>
            <option value="preview">preview</option>
            <option value="execute">execute</option>
          </select>
        </div>
      </div>

      <div style={{ marginTop: '0.75rem' }}>
        <div style={s.formLabel}>{t('enforcementAdmin.test.context')}</div>
        <textarea
          style={s.textarea}
          placeholder={t('enforcementAdmin.test.contextPlaceholder')}
          value={testContextText}
          onChange={e => setTestContextText(e.target.value)}
        />
      </div>

      <div style={s.buttonRow}>
        <button style={s.btnPrimary} onClick={handleRun}>
          {t('enforcementAdmin.test.run')}
        </button>
      </div>

      {testResult && (
        <div style={{ marginTop: '1rem' }}>
          <div style={s.formLabel}>{t('enforcementAdmin.test.result')}</div>
          <pre style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6',
            overflowX: 'auto',
            fontSize: '0.8125rem',
            margin: 0,
          }}>
            {JSON.stringify(testResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
