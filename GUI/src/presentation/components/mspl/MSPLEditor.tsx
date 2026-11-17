import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks';
import PolicyBuilder from './PolicyBuilder';
import XmlViewer from './XmlViewer';
import { buildXmlFromObject, parseXmlToObject, type Schema } from './helpers';

const ROOT_TYPE = 'ITResourceOrchestrationType';
const ROOT_TAG = 'ITResourceOrchestration';
type EditorInputMode = 'builder' | 'manual';

interface MSPLEditorProps {
  schema?: Schema;
  initialData?: Record<string, unknown> | string; // Puede ser objeto o XML string
  onChange?: (data: Record<string, unknown>) => void;
  onApply?: (msplXml: string, name?: string) => void;
}

/**
 * MSPLEditor - Componente que combina PolicyBuilder y XmlViewer
 * Permite crear/editar políticas MSPL visualmente
 */
export default function MSPLEditor({ schema, initialData, onChange, onApply }: MSPLEditorProps): JSX.Element {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  
  // Parsear initialData si es XML string
  const parseInitialData = (): Record<string, unknown> => {
    if (!initialData) return {};
    if (typeof initialData === 'string') {
      try {
        return parseXmlToObject(initialData);
      } catch (error) {
        console.error('Error parsing XML initialData:', error);
        return {};
      }
    }
    return initialData;
  };

  const [formData, setFormData] = useState<Record<string, unknown>>(parseInitialData());
  const [policyName, setPolicyName] = useState<string>('');
  const [inputMode, setInputMode] = useState<EditorInputMode>('builder');
  const [manualXml, setManualXml] = useState<string>(typeof initialData === 'string' ? initialData : '');

  // Cargar esquema si no se proporciona
  const [loadedSchema, setLoadedSchema] = useState<Schema | undefined>(schema);

  useEffect(() => {
    if (!loadedSchema) {
      fetch('/mspl_schema_summary.json')
        .then(res => res.json())
        .then(data => setLoadedSchema(data as Schema))
        .catch(err => console.error('Error loading schema:', err));
    }
  }, [loadedSchema]);

  // Generar ID por defecto si no existe (igual que en frontend-bastion)
  useEffect(() => {
    if (!formData.id && loadedSchema) {
      const defaultId = `omspl_${crypto.randomUUID().replace(/-/g, '')}`;
      const newFormData = {
        id: defaultId,
        xmlns: "http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd mspl.xsd"
      };
      setFormData(newFormData);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadedSchema]); // Solo ejecutar cuando se carga el schema, no cuando cambia formData.id

  const handleChange = (updatedData: Record<string, unknown>): void => {
    setFormData(updatedData);
    if (onChange) {
      onChange(updatedData);
    }
  };

  const notifyXmlParsed = (xml: string): void => {
    if (!onChange) {
      return;
    }
    try {
      const parsed = parseXmlToObject(xml);
      if (parsed && typeof parsed === 'object') {
        onChange(parsed);
      }
    } catch {
      // Ignore parse errors while typing or uploading potentially invalid XML.
    }
  };

  const handleManualXmlChange = (value: string): void => {
    setManualXml(value);
    notifyXmlParsed(value);
  };

  const handleXmlFileUpload = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const content = typeof reader.result === 'string' ? reader.result : '';
      setManualXml(content);
      notifyXmlParsed(content);
    };
    reader.onerror = () => {
      console.error('Error reading XML file');
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const handleApply = (): void => {
    if (onApply) {
      const xmlString = inputMode === 'manual'
        ? manualXml
        : buildXmlFromObject(ROOT_TAG, formData, {
            prettyPrint: true,
            allowEmptyTags: true,
          });
      onApply(xmlString, policyName.trim() || undefined);
    }
  };

  if (!loadedSchema) {
    return <p>{t('policies.createEdit.loadingSchema')}</p>;
  }

  return (
    <div style={{ padding: isMobile ? '0.5rem' : '2rem' }}>
      {/* Campo de nombre de la política */}
      {onApply && (
        <div style={{ 
          marginBottom: isMobile ? '1rem' : '2rem', 
          padding: isMobile ? '0.75rem' : '1rem', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '0.5rem', 
            fontWeight: 'bold',
            fontSize: isMobile ? '0.9rem' : '1rem'
          }}>
            {t('policies.createEdit.policyName') || 'Nombre de la política'}:
          </label>
          <input
            type="text"
            value={policyName}
            onChange={(e) => setPolicyName(e.target.value)}
            placeholder={t('policies.createEdit.policyNamePlaceholder') || 'Ingrese un nombre para la política (opcional)'}
            style={{
              width: '100%',
              padding: isMobile ? '0.5rem' : '0.75rem',
              fontSize: isMobile ? '0.9rem' : '1rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              boxSizing: 'border-box'
            }}
          />
        </div>
      )}

      {onApply && (
        <div style={{
          marginBottom: isMobile ? '1rem' : '2rem',
          padding: isMobile ? '0.75rem' : '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            fontWeight: 'bold',
            fontSize: isMobile ? '0.9rem' : '1rem'
          }}>
            {t('policies.createEdit.inputMode')}:
          </label>
          <div style={{
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '0.75rem'
          }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="radio"
                name="msplInputMode"
                checked={inputMode === 'builder'}
                onChange={() => setInputMode('builder')}
              />
              {t('policies.createEdit.builderMode')}
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="radio"
                name="msplInputMode"
                checked={inputMode === 'manual'}
                onChange={() => setInputMode('manual')}
              />
              {t('policies.createEdit.manualMode')}
            </label>
          </div>
        </div>
      )}
      
      {inputMode === 'builder' ? (
        <div style={{ 
          display: 'flex', 
          flexDirection: isMobile ? 'column' : 'row',
          gap: isMobile ? '1rem' : '2rem', 
          marginTop: isMobile ? '1rem' : '2rem' 
        }}>
          <div style={{ 
            flex: isMobile ? 'none' : '1 1 50%',
            minWidth: isMobile ? undefined : 0,
            borderRight: isMobile ? 'none' : '1px solid #ccc', 
            borderBottom: isMobile ? '1px solid #ccc' : 'none',
            paddingRight: isMobile ? 0 : '2rem',
            paddingBottom: isMobile ? '1rem' : 0
          }}>
            <PolicyBuilder
              type={ROOT_TYPE}
              schema={loadedSchema}
              data={formData}
              onChange={handleChange}
            />
          </div>

          <div style={{
            flex: isMobile ? 'none' : '1 1 50%',
            minWidth: isMobile ? undefined : 0,
            maxWidth: '100%',
            overflowX: 'auto',
          }}>
            <XmlViewer rootTag={ROOT_TAG} data={formData} />
          </div>
        </div>
      ) : (
        <div style={{
          marginTop: isMobile ? '1rem' : '2rem',
          padding: isMobile ? '0.75rem' : '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <p style={{ marginTop: 0 }}>
            {t('policies.createEdit.manualModeDescription')}
          </p>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              {t('policies.createEdit.uploadXml')}
            </label>
            <input
              type="file"
              accept=".xml,text/xml,application/xml"
              onChange={handleXmlFileUpload}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              {t('policies.createEdit.pasteXml')}
            </label>
            <textarea
              value={manualXml}
              onChange={(event) => handleManualXmlChange(event.target.value)}
              placeholder={t('policies.createEdit.pasteXmlPlaceholder')}
              rows={isMobile ? 14 : 18}
              style={{
                width: '100%',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                padding: '0.75rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                boxSizing: 'border-box'
              }}
            />
          </div>
        </div>
      )}

      {onApply && (
        <div style={{ marginTop: isMobile ? '1rem' : '2rem', textAlign: 'center' }}>
          <button 
            onClick={handleApply}
            style={{
              width: isMobile ? '100%' : 'auto',
              padding: isMobile ? '1rem 2rem' : '0.75rem 2rem',
              fontSize: '1rem',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {t('policies.createEdit.applyButton')}
          </button>
        </div>
      )}
    </div>
  );
}
