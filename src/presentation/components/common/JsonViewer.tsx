import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface JsonViewerProps {
  data: unknown;
  title?: string;
}

/**
 * JsonViewer - Componente para visualizar JSON formateado
 */
export default function JsonViewer({ data, title }: JsonViewerProps): JSX.Element {
  const { t } = useTranslation();
  const displayTitle = title || t('jsonViewer.title');

  if (!data) {
    return <p>{t('jsonViewer.noData')}</p>;
  }

  const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

  return (
    <div style={{ marginTop: '1rem' }}>
      <h3>{displayTitle}</h3>
      <SyntaxHighlighter 
        language="json" 
        style={oneDark} 
        wrapLines={true}
        customStyle={{
          borderRadius: '6px',
          padding: '1rem',
          fontSize: '14px'
        }}
      >
        {jsonString}
      </SyntaxHighlighter>
    </div>
  );
}

