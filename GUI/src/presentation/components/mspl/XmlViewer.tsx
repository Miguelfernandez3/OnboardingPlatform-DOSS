import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { buildXmlFromObject } from './helpers';

interface XmlViewerProps {
  rootTag: string;
  data: Record<string, unknown>;
}

/**
 * XmlViewer - Componente para visualizar XML formateado
 * Adaptado de frontend-bastion
 */
export default function XmlViewer({ rootTag, data }: XmlViewerProps): JSX.Element {
  const { t } = useTranslation();

  if (!data || Object.keys(data).length === 0) return <p>{t('xmlViewer.noData')}</p>;
  if (!data || typeof data !== 'object') return <p>{t('xmlViewer.invalidData')}</p>;

  const xml = buildXmlFromObject(rootTag, data, { prettyPrint: true, allowEmptyTags: true });

  return (
    <div>
      <h3>{t('xmlViewer.title')}</h3>
      <SyntaxHighlighter 
        language="xml" 
        style={oneDark} 
        wrapLines={true}
        customStyle={{
          borderRadius: '6px',
          padding: '1rem',
          fontSize: '14px'
        }}
      >
        {xml}
      </SyntaxHighlighter>
    </div>
  );
}

