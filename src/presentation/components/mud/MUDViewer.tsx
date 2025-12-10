import { useTranslation } from 'react-i18next';
import { MUD } from '../../../core/domain/entities/MUD';
import JsonViewer from '../common/JsonViewer';

interface MUDViewerProps {
  mud: MUD | null;
}

/**
 * MUDViewer - Componente para visualizar archivos MUD
 */
export default function MUDViewer({ mud }: MUDViewerProps): JSX.Element {
  const { t } = useTranslation();

  if (!mud) {
    return <p>{t('device.mud.noData')}</p>;
  }

  return (
    <div>
      <h2>{t('device.mud.title')}</h2>
      <div style={{ marginBottom: '1rem' }}>
        <p><strong>{t('device.mud.version')}:</strong> {mud.mudVersion || 'N/A'}</p>
        <p><strong>{t('device.mud.url')}:</strong> {mud.mudUrl || 'N/A'}</p>
        <p><strong>{t('device.mud.manufacturer')}:</strong> {mud.mfgName || 'N/A'}</p>
        <p><strong>{t('device.mud.model')}:</strong> {mud.modelName || 'N/A'}</p>
        <p><strong>{t('device.mud.lastUpdate')}:</strong> {mud.lastUpdate || 'N/A'}</p>
      </div>
      <JsonViewer data={mud.mudData || mud} title={t('device.mud.title')} />
    </div>
  );
}

