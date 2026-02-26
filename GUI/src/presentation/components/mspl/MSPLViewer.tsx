import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { XMLParser, XMLBuilder } from 'fast-xml-parser';

interface MSPLViewerProps {
  msplXml: string;
  title?: string;
}

/**
 * Formatea XML usando fast-xml-parser para parsear y reconstruir con formato
 */
function formatXml(xml: string): string {
  if (!xml || typeof xml !== 'string') {
    return xml;
  }

  const trimmed = xml.trim();
  
  // Si ya está formateado (contiene saltos de línea múltiples y tiene indentación), retornar tal cual
  const lines = trimmed.split('\n');
  if (lines.length > 1 && lines.some(line => line.trim().startsWith('<') && line !== line.trim())) {
    // Ya tiene indentación, está formateado
    return trimmed;
  }

  try {
    // Intentar con preserveOrder primero (para mantener el orden exacto)
    const parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: '@_',
      textNodeName: '#text',
      preserveOrder: true,
      trimValues: false
    });
    
    const jsonObj = parser.parse(trimmed);
    
    // Reconstruir XML con formato
    const builder = new XMLBuilder({
      ignoreAttributes: false,
      attributeNamePrefix: '@_',
      textNodeName: '#text',
      format: true,
      indentBy: '  ',
      preserveOrder: true,
      suppressEmptyNode: false
    });
    
    const formatted = builder.build(jsonObj);
    
    // Verificar que el formateo funcionó (debe tener múltiples líneas)
    if (formatted.split('\n').length > 1) {
      return formatted;
    }
    
    // Si no funcionó, intentar sin preserveOrder
    throw new Error('Formatting with preserveOrder did not produce multiple lines');
  } catch (error) {
    // Si falla con preserveOrder, intentar sin preserveOrder
    try {
      const parser2 = new XMLParser({
        ignoreAttributes: false,
        attributeNamePrefix: '@_',
        trimValues: false
      });
      
      const jsonObj2 = parser2.parse(trimmed);
      
      const builder2 = new XMLBuilder({
        ignoreAttributes: false,
        attributeNamePrefix: '@_',
        format: true,
        indentBy: '  ',
        suppressEmptyNode: false
      });
      
      const formatted2 = builder2.build(jsonObj2);
      
      if (formatted2.split('\n').length > 1) {
        return formatted2;
      }
      
      // Si aún no funciona, usar formateo manual básico
      return formatXmlManual(trimmed);
    } catch (error2) {
      console.warn('Error formatting XML with fast-xml-parser, using manual formatting:', error2);
      return formatXmlManual(trimmed);
    }
  }
}

/**
 * Formateo manual básico de XML usando regex
 * Esta función procesa el XML tag por tag y agrega indentación apropiada
 */
function formatXmlManual(xml: string): string {
  let formatted = '';
  let indent = 0;
  const tab = '  ';
  
  // Remover espacios en blanco innecesarios entre tags pero mantener el contenido de texto
  let cleaned = xml.replace(/>\s+</g, '><');
  
  // Procesar el XML caracter por caracter para manejar correctamente los tags
  let i = 0;
  let currentTag = '';
  let inQuotes = false;
  let quoteChar = '';
  
  while (i < cleaned.length) {
    const char = cleaned[i];
    
    if (char === '"' || char === "'") {
      if (!inQuotes) {
        inQuotes = true;
        quoteChar = char;
      } else if (char === quoteChar) {
        inQuotes = false;
        quoteChar = '';
      }
      currentTag += char;
    } else if (char === '<' && !inQuotes) {
      // Inicio de tag
      if (currentTag.trim()) {
        // Hay contenido antes del tag, agregarlo con indentación
        formatted += tab.repeat(indent) + currentTag.trim() + '\n';
        currentTag = '';
      }
      currentTag += char;
    } else if (char === '>' && !inQuotes) {
      // Fin de tag
      currentTag += char;
      const tag = currentTag.trim();
      
      if (tag.startsWith('<?xml')) {
        // Declaración XML
        formatted += tag + '\n';
      } else if (tag.startsWith('</')) {
        // Tag de cierre - reducir indentación antes de escribir
        indent = Math.max(0, indent - 1);
        formatted += tab.repeat(indent) + tag + '\n';
      } else if (tag.endsWith('/>')) {
        // Tag auto-cerrado
        formatted += tab.repeat(indent) + tag + '\n';
      } else {
        // Tag de apertura
        formatted += tab.repeat(indent) + tag + '\n';
        indent++;
      }
      
      currentTag = '';
    } else {
      currentTag += char;
    }
    
    i++;
  }
  
  // Agregar cualquier contenido restante
  if (currentTag.trim()) {
    formatted += tab.repeat(indent) + currentTag.trim();
  }
  
  return formatted.trim();
}

/**
 * MSPLViewer - Componente para visualizar políticas MSPL en formato XML
 */
export default function MSPLViewer({ msplXml, title: _title }: MSPLViewerProps): JSX.Element {
  const { t } = useTranslation();
  
  // Formatear el XML antes de mostrarlo (usar useMemo para evitar recalcular)
  const formattedXml = useMemo(() => {
    if (!msplXml) {
      return '';
    }
    return formatXml(msplXml);
  }, [msplXml]);
  
  if (!msplXml) {
    return <p>{t('policies.noPolicies')}</p>;
  }

  return (
    <div style={{ width: '100%', overflow: 'auto' }}>
      <SyntaxHighlighter 
        language="xml" 
        style={oneDark} 
        wrapLines={false}
        customStyle={{
          borderRadius: '6px',
          padding: '0.5rem',  
          fontSize: '14px',
          margin: 0,
          whiteSpace: 'pre',
          wordWrap: 'normal',
          overflowWrap: 'normal',
          display: 'block'
        }}
        PreTag="pre"
        codeTagProps={{ style: { display: 'block', whiteSpace: 'pre' } }}
      >
        {formattedXml}
      </SyntaxHighlighter>
    </div>
  );
}
