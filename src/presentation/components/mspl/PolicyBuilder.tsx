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
}

interface NavigationItem {
  parentType: string;
  parentData: Record<string, unknown>;
  fieldName: string;
}

interface PendingSubType {
  fieldName: string;
  baseType: string;
}

/**
 * PolicyBuilder - Componente para construir políticas MSPL
 * Adaptado de frontend-bastion
 */
export default function PolicyBuilder({ type, schema, data, onChange }: PolicyBuilderProps): JSX.Element {
  const { t } = useTranslation();
  const [navigationStack, setNavigationStack] = useState<NavigationItem[]>([]);
  const [currentType, setCurrentType] = useState<string>(type);
  const [currentData, setCurrentData] = useState<Record<string, unknown>>(data);
  const [pendingSubType, setPendingSubType] = useState<PendingSubType | null>(null);
  const [subtypeOptions, setSubtypeOptions] = useState<string[]>([]);

  // Tipo efectivo desde @xsi:type si existe
  const effectiveType = getEffectiveType(currentType, currentData);

  const typeDef = getTypeDefinition(schema, effectiveType);
  if (!typeDef) return <p>No se encontró la definición para {effectiveType}</p>;

  const propagateChangeUp = (newData: Record<string, unknown>): void => {
    if (navigationStack.length === 0) {
      onChange(newData);
    } else {
      let updated = newData;
      for (let i = navigationStack.length - 1; i >= 0; i--) {
        const { fieldName, parentData } = navigationStack[i];
        updated = { ...parentData, [fieldName]: updated };
      }
      onChange(updated);
    }
  };

  const handleFieldChange = (fieldName: string, value: string): void => {
    const newData = { ...currentData, [fieldName]: value };
    setCurrentData(newData);
    propagateChangeUp(newData);
  };

  const handleRemoveField = (fieldName: string): void => {
    const newData = { ...currentData };
    delete newData[fieldName];
    setCurrentData(newData);
    propagateChangeUp(newData);
  };


  const handleAddField = (fieldName: string, isComplex: boolean, rawType: string): void => {
    let fieldType = cleanTypeName(rawType);

    if (currentData[fieldName]) {
      if (isComplex) {
        const fieldValue = currentData[fieldName] as Record<string, unknown>;
        const subTypeFromValue = fieldValue['@xsi:type'];
        if (subTypeFromValue) {
          fieldType = cleanTypeName(String(subTypeFromValue));
        }
        setNavigationStack((prev) => [
          ...prev,
          { parentType: currentType, parentData: currentData, fieldName },
        ]);
        setCurrentType(fieldType);
        setCurrentData(fieldValue);
      }
      return;
    }

    if (isComplex) {
      const subtypes = getSubtypes(schema, fieldType);
      if (subtypes.length > 0) {
        setPendingSubType({ fieldName, baseType: fieldType });
        setSubtypeOptions(subtypes);
        return;
      }
    }

    createField(fieldName, fieldType, isComplex);
  };

  const createField = (fieldName: string, fieldType: string, isComplex: boolean, chosenSubtype: string | null = null): void => {
    let initialValue: unknown;
    let actualType = fieldType;
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
        actualType = cleanTypeName(chosenSubtype);
      }
    } else {
      initialValue = '';
    }

    const newData = { ...currentData, [fieldName]: initialValue };
    setCurrentData(newData);
    propagateChangeUp(newData);

    if (isComplex) {
      setNavigationStack((prev) => [
        ...prev,
        { parentType: currentType, parentData: newData, fieldName },
      ]);
      setCurrentType(actualType);
      setCurrentData(initialValue as Record<string, unknown>);
    }
  };

  const handleSubtypeSelect = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const chosen = e.target.value;
    if (pendingSubType) {
      createField(pendingSubType.fieldName, pendingSubType.baseType, true, chosen);
      setPendingSubType(null);
      setSubtypeOptions([]);
    }
  };

  const handleGoBack = (): void => {
    const prev = [...navigationStack];
    const last = prev.pop();
    if (last) {
      setCurrentType(last.parentType);
      setCurrentData(last.parentData);
      setNavigationStack(prev);
    }
  };

  const renderField = (field: { name: string; type: string }): JSX.Element => {
    const fieldName = cleanFieldName(field.name);
    const fieldValue = currentData[field.name];

    let fieldType = cleanTypeName(field.type);
    if (typeof fieldValue === 'object' && fieldValue && (fieldValue as Record<string, unknown>)['@xsi:type']) {
      fieldType = cleanTypeName(String((fieldValue as Record<string, unknown>)['@xsi:type']));
    }

    const isComplex = isComplexType(schema, fieldType);
    const allowDelete = !(navigationStack.length === 0 && currentType === 'ITResourceOrchestrationType');

    return (
      <div className="field-block" key={field.name}>
        <span className="field-name">{fieldName}</span>
        {isComplex ? (
          <button
            className="small-button"
            onClick={() => {
              setNavigationStack((prev) => [
                ...prev,
                { parentType: currentType, parentData: currentData, fieldName: field.name },
              ]);
              setCurrentType(fieldType);
              setCurrentData(fieldValue as Record<string, unknown>);
            }}
          >
            ➔ {t('policyBuilder.goTo')} {fieldType}
          </button>
        ) : (
          <input
            className="input-text"
            type="text"
            value={(fieldValue as string) || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
          />
        )}
        {allowDelete && (
          <button
            className="delete-button"
            onClick={() => handleRemoveField(field.name)}
                    title={t('policyBuilder.removeField')}
          >
            🗑️
          </button>
        )}
      </div>
    );
  };

  const addedFields = Object.keys(currentData);
  const missingFields = typeDef.fields.filter((f) => !addedFields.includes(f.name));

  return (
    <div className="policy-builder">
      {navigationStack.length > 0 && (
        <button className="back-button" onClick={handleGoBack}>
          ⬅️ {t('policyBuilder.backTo')} {navigationStack[navigationStack.length - 1].parentType}
        </button>
      )}

      <h3>{effectiveType}</h3>

      {(effectiveType === 'ITResourceOrchestrationType' || effectiveType === 'ITResourceType') && (
        <div style={{ marginBottom: '1rem' }}>
          <label>ID:</label>
          <input
            className="input-text"
            type="text"
            value={(currentData.id as string) || ''}
            onChange={(e) => handleFieldChange('id', e.target.value)}
          />
        </div>
      )}

      {typeDef.fields.filter((f) => addedFields.includes(f.name)).map(renderField)}

      {missingFields.length > 0 && (
        <div className="optional-fields">
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

      {pendingSubType && (
        <div style={{ marginTop: '1rem' }}>
          <label>{t('policyBuilder.selectSubtype')} {cleanFieldName(pendingSubType.fieldName)}:</label>
          <select onChange={handleSubtypeSelect} defaultValue="">
            <option value="" disabled>{t('policyBuilder.chooseOne')}</option>
            {subtypeOptions.map((st) => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}

