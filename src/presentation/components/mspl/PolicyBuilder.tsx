import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './PolicyBuilder.css';
import {
  cleanFieldName,
  cleanTypeName,
  getSubtypes,
  getEffectiveType,
  isComplexType,
  getTypeDefinition,
  type Schema,
} from './helpers';

interface PolicyBuilderProps {
  type: string;
  schema: Schema;
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
  level?: number; // Nivel de indentación (para recursión)
  path?: string; // Ruta del campo para identificar cambios
}

interface PendingSubType {
  fieldName: string;
  baseType: string;
}

/**
 * PolicyBuilder - Componente recursivo con desplegables para construir políticas MSPL
 * Versión mejorada con UI tipo accordion y indentación visual
 */
export default function PolicyBuilder({ 
  type, 
  schema, 
  data, 
  onChange, 
  level = 0,
  path = 'root'
}: PolicyBuilderProps): JSX.Element {
  const { t } = useTranslation();
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const [pendingSubType, setPendingSubType] = useState<PendingSubType | null>(null);
  const [subtypeOptions, setSubtypeOptions] = useState<string[]>([]);

  // Tipo efectivo desde @xsi:type si existe
  const effectiveType = getEffectiveType(type, data);
  const typeDef = getTypeDefinition(schema, effectiveType);
  
  if (!typeDef) return <p>{t('policyBuilder.noDefinition', { type: effectiveType })}</p>;

  const toggleField = (fieldName: string): void => {
    setExpandedFields(prev => {
      const next = new Set(prev);
      if (next.has(fieldName)) {
        next.delete(fieldName);
      } else {
        next.add(fieldName);
      }
      return next;
    });
  };

  const handleFieldChange = (fieldName: string, value: string): void => {
    const newData = { ...data, [fieldName]: value };
    onChange(newData);
  };

  const handleRemoveField = (fieldName: string): void => {
    const newData = { ...data };
    delete newData[fieldName];
    onChange(newData);
    // Cerrar el desplegable si estaba abierto
    setExpandedFields(prev => {
      const next = new Set(prev);
      next.delete(fieldName);
      return next;
    });
  };

  const handleNestedChange = (fieldName: string) => (newNestedData: Record<string, unknown>): void => {
    const newData = { ...data, [fieldName]: newNestedData };
    onChange(newData);
  };

  const handleAddField = (fieldName: string, isComplex: boolean, rawType: string): void => {
    // Si el campo ya existe, expandirlo en lugar de recrearlo
    if (data[fieldName]) {
      if (isComplex) {
        setExpandedFields(prev => new Set(prev).add(fieldName));
      }
      return;
    }

    if (isComplex) {
      const fieldType = cleanTypeName(rawType);
      const subtypes = getSubtypes(schema, fieldType);
      if (subtypes.length > 0) {
        setPendingSubType({ fieldName, baseType: fieldType });
        setSubtypeOptions(subtypes);
        return;
      }
    }

    createField(fieldName, cleanTypeName(rawType), isComplex);
  };

  const createField = (fieldName: string, fieldType: string, isComplex: boolean, chosenSubtype: string | null = null): void => {
    let initialValue: unknown;
    
    if (isComplex) {
      if (fieldType === 'ITResourceType') {
        initialValue = {
          id: `mspl_${crypto.randomUUID().replace(/-/g, '')}`,
          orchestrationID: (data.id as string) || '',
        };
      } else {
        initialValue = {};
      }
      if (chosenSubtype) {
        (initialValue as Record<string, unknown>)['@xsi:type'] = chosenSubtype;
      }
      // Auto-expandir campos complejos recién creados
      setExpandedFields(prev => new Set(prev).add(fieldName));
    } else {
      initialValue = '';
    }

    const newData = { ...data, [fieldName]: initialValue };
    onChange(newData);
  };

  const handleSubtypeSelect = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const chosen = e.target.value;
    if (pendingSubType) {
      createField(pendingSubType.fieldName, pendingSubType.baseType, true, chosen);
      setPendingSubType(null);
      setSubtypeOptions([]);
    }
  };

  const renderField = (field: { name: string; type: string }): JSX.Element => {
    const fieldName = cleanFieldName(field.name);
    const fieldValue = data[field.name];
    const isExpanded = expandedFields.has(field.name);

    let fieldType = cleanTypeName(field.type);
    if (typeof fieldValue === 'object' && fieldValue && (fieldValue as Record<string, unknown>)['@xsi:type']) {
      fieldType = cleanTypeName(String((fieldValue as Record<string, unknown>)['@xsi:type']));
    }

    const isComplex = isComplexType(schema, fieldType);
    // Permitir borrar todos los campos excepto el ID en el nivel raíz
    const allowDelete = !(level === 0 && field.name === 'id');

    return (
      <div className={`field-block field-level-${level}`} key={field.name}>
        <div className="field-header">
          <span className="field-name">{fieldName}</span>
          {isComplex ? (
            <>
              <button
                className="expand-button"
                onClick={() => toggleField(field.name)}
                title={isExpanded ? t('policyBuilder.collapse') : t('policyBuilder.expand')}
              >
                {isExpanded ? '▼' : '▶'} {fieldType}
              </button>
              {allowDelete && (
                <button
                  className="delete-button"
                  onClick={() => handleRemoveField(field.name)}
                  title={t('policyBuilder.removeField')}
                >
                  ×
                </button>
              )}
            </>
          ) : (
            <>
              <input
                className="input-text"
                type="text"
                value={(fieldValue as string) || ''}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
              />
              {allowDelete && (
                <button
                  className="delete-button"
                  onClick={() => handleRemoveField(field.name)}
                  title={t('policyBuilder.removeField')}
                >
                  ×
                </button>
              )}
            </>
          )}
        </div>
        
        {isComplex && isExpanded && fieldValue !== null && typeof fieldValue === 'object' && !Array.isArray(fieldValue) && (
          <div className="field-content">
            <PolicyBuilder
              type={fieldType}
              schema={schema}
              data={fieldValue as Record<string, unknown>}
              onChange={handleNestedChange(field.name)}
              level={level + 1}
              path={`${path}.${field.name}`}
            />
          </div>
        )}
      </div>
    );
  };

  const addedFields = Object.keys(data).filter(key => !key.startsWith('@') && !key.startsWith('xmlns') && key !== 'xsi:schemaLocation');
  const missingFields = typeDef.fields.filter((f) => !addedFields.includes(f.name));

  return (
    <div className={`policy-builder policy-level-${level}`}>
      {level === 0 && (
        <h3 className="builder-title">{effectiveType}</h3>
      )}

      {(effectiveType === 'ITResourceOrchestrationType' || effectiveType === 'ITResourceType') && level === 0 && (
        <div className="field-block field-level-0">
          <div className="field-header">
            <span className="field-name">ID</span>
            <input
              className="input-text"
              type="text"
              value={(data.id as string) || ''}
              onChange={(e) => handleFieldChange('id', e.target.value)}
            />
          </div>
        </div>
      )}

      {typeDef.fields.filter((f) => addedFields.includes(f.name)).map(renderField)}

      {(missingFields.length > 0 || pendingSubType) && (
        <div className={`optional-fields optional-level-${level}`}>
          {pendingSubType && (
            <div className="subtype-selector">
              <label>
                {t('policyBuilder.selectSubtype')} {cleanFieldName(pendingSubType.fieldName)}:
              </label>
              <select onChange={handleSubtypeSelect} defaultValue="">
                <option value="" disabled>{t('policyBuilder.chooseOne')}</option>
                {subtypeOptions.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </div>
          )}
          {missingFields.map((f) => {
            const name = cleanFieldName(f.name);
            const isComplex = isComplexType(schema, f.type);
            return (
              <button
                className="add-button"
                key={f.name}
                onClick={() => handleAddField(f.name, isComplex, f.type)}
              >
                ➕ {t('policyBuilder.addField')} {name}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

