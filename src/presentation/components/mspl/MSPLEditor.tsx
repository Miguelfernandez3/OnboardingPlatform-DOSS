import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PolicyBuilder from './PolicyBuilder';
import XmlViewer from './XmlViewer';
import { buildXmlFromObject, parseXmlToObject, type Schema } from './helpers';

const ROOT_TYPE = 'ITResourceOrchestrationType';
const ROOT_TAG = 'ITResourceOrchestration';

interface MSPLEditorProps {
  schema?: Schema;
  initialData?: Record<string, unknown> | string; // Puede ser objeto o XML string
  onChange?: (data: Record<string, unknown>) => void;
  onApply?: (msplXml: string) => void;
}

/**
 * MSPLEditor - Componente que combina PolicyBuilder y XmlViewer
 * Permite crear/editar políticas MSPL visualmente
 */
export default function MSPLEditor({ schema, initialData, onChange, onApply }: MSPLEditorProps): JSX.Element {
  const { t } = useTranslation();
  
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

  const handleApply = (): void => {
    if (onApply) {
      // Generar XML desde formData usando el helper
      const xmlString = buildXmlFromObject(ROOT_TAG, formData, {
        prettyPrint: true,
        allowEmptyTags: true,
      });
      onApply(xmlString);
    }
  };

  if (!loadedSchema) {
    return <p>{t('policies.createEdit.loadingSchema')}</p>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', gap: '2rem', marginTop: '2rem' }}>
        <div style={{ flex: 4, borderRight: '1px solid #ccc', paddingRight: '2rem' }}>
          <PolicyBuilder
            type={ROOT_TYPE}
            schema={loadedSchema}
            data={formData}
            onChange={handleChange}
          />
        </div>

        <div style={{
          flex: 6,
          maxWidth: '100%',
          overflowX: 'auto',
        }}>
          <XmlViewer rootTag={ROOT_TAG} data={formData} />
        </div>
      </div>

      {onApply && (
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button 
            onClick={handleApply}
            style={{
              padding: '0.75rem 2rem',
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

