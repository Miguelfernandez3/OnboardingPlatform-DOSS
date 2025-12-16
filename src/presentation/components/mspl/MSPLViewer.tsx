import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MSPLViewerProps {
  msplXml: string;
  title?: string;
}

/**
 * MSPLViewer - Componente para visualizar políticas MSPL en formato XML
 */
export default function MSPLViewer({ msplXml, title }: MSPLViewerProps): JSX.Element {
  const { t } = useTranslation();
  // const displayTitle = title || t('policies.title');

  if (!msplXml) {
    return <p>{t('policies.noPolicies')}</p>;
  }

  return (
    <div>
      {/* <h3>{displayTitle}</h3> */}
      <SyntaxHighlighter 
        language="xml" 
        style={oneDark} 
        wrapLines={true}
        customStyle={{
          borderRadius: '6px',
          padding: '0.5rem',  
          fontSize: '14px'
        }}
      >
        {msplXml}
      </SyntaxHighlighter>
    </div>
  );
}

