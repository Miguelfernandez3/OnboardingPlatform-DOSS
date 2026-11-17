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
import {
  createEmptyConfigurationRule,
  DEFAULT_ACTION_OPTIONS,
  getRuleSetFieldLabelKey,
  isDefaultActionField,
  isRepeatableField,
  normalizeToArray,
  readDefaultActionValue,
  type DefaultActionValue,
} from './helpers/builderConfig';

interface PolicyBuilderProps {
  type: string;
  schema: Schema;
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
  level?: number;
  path?: string;
}

interface PendingSubType {
  fieldName: string;
  baseType: string;
}

/**
 * PolicyBuilder - Componente recursivo con desplegables para construir políticas MSPL
 */
export default function PolicyBuilder({
  type,
  schema,
  data,
  onChange,
  level = 0,
  path = 'root',
}: PolicyBuilderProps): JSX.Element {
  const { t } = useTranslation();
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const [pendingSubType, setPendingSubType] = useState<PendingSubType | null>(null);
  const [subtypeOptions, setSubtypeOptions] = useState<string[]>([]);

  const effectiveType = getEffectiveType(type, data);
  const typeDef = getTypeDefinition(schema, effectiveType);

  if (!typeDef) return <p>{t('policyBuilder.noDefinition', { type: effectiveType })}</p>;

  const toggleField = (fieldName: string): void => {
    setExpandedFields((prev) => {
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
    setExpandedFields((prev) => {
      const next = new Set(prev);
      next.delete(fieldName);
      return next;
    });
  };

  const handleNestedChange = (fieldName: string) => (newNestedData: Record<string, unknown>): void => {
    const newData = { ...data, [fieldName]: newNestedData };
    onChange(newData);
  };

  const getFieldDisplayName = (field: { name: string }): string => {
    const labelKey = getRuleSetFieldLabelKey(field.name);
    if (effectiveType === 'RuleSetConfiguration' && labelKey) {
      return t(`policyBuilder.fieldLabels.${labelKey}`);
    }
    return cleanFieldName(field.name);
  };

  const createField = (
    fieldName: string,
    fieldType: string,
    isComplex: boolean,
    chosenSubtype: string | null = null
  ): void => {
    let initialValue: unknown;

    if (isRepeatableField(fieldName)) {
      initialValue = [createEmptyConfigurationRule()];
      setExpandedFields((prev) => new Set(prev).add(fieldName));
    } else if (isComplex) {
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
      setExpandedFields((prev) => new Set(prev).add(fieldName));
    } else {
      initialValue = '';
    }

    onChange({ ...data, [fieldName]: initialValue });
  };

  const handleAddField = (fieldName: string, isComplex: boolean, rawType: string): void => {
    if (isRepeatableField(fieldName)) {
      const current = normalizeToArray(data[fieldName]);
      onChange({
        ...data,
        [fieldName]: [...current, createEmptyConfigurationRule()],
      });
      setExpandedFields((prev) => new Set(prev).add(fieldName));
      return;
    }

    if (data[fieldName]) {
      if (isComplex) {
        setExpandedFields((prev) => new Set(prev).add(fieldName));
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

  const handleSubtypeSelect = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const chosen = e.target.value;
    if (pendingSubType) {
      createField(pendingSubType.fieldName, pendingSubType.baseType, true, chosen);
      setPendingSubType(null);
      setSubtypeOptions([]);
    }
  };

  const handleRepeatableItemChange =
    (fieldName: string, index: number) =>
    (newItemData: Record<string, unknown>): void => {
      const items = [...normalizeToArray(data[fieldName])];
      items[index] = newItemData;
      onChange({ ...data, [fieldName]: items });
    };

  const handleRemoveRepeatableItem = (fieldName: string, index: number): void => {
    const items = normalizeToArray(data[fieldName]).filter((_, i) => i !== index);
    if (items.length === 0) {
      const newData = { ...data };
      delete newData[fieldName];
      onChange(newData);
      return;
    }
    onChange({ ...data, [fieldName]: items });
  };

  const defaultActionField = typeDef.fields.find(
    (f) => isDefaultActionField(f.name, effectiveType)
  );

  const handleDefaultActionChange = (value: DefaultActionValue): void => {
    if (!defaultActionField) return;
    if (!value) {
      const newData = { ...data };
      delete newData[defaultActionField.name];
      onChange(newData);
      return;
    }
    onChange({ ...data, [defaultActionField.name]: value });
  };

  const renderDefaultActionSelector = (): JSX.Element | null => {
    if (!defaultActionField) return null;
    const currentValue = readDefaultActionValue(data[defaultActionField.name]);

    return (
      <div className={`field-block field-level-${level} default-action-field`}>
        <div className="field-header">
          <span className="field-name">{t('policyBuilder.defaultAction')}</span>
          <select
            className="input-select"
            value={currentValue}
            onChange={(e) => handleDefaultActionChange(e.target.value as DefaultActionValue)}
          >
            <option value="">{t('policyBuilder.defaultActionNone')}</option>
            {DEFAULT_ACTION_OPTIONS.filter((opt) => opt !== '').map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      </div>
    );
  };

  const renderRepeatableField = (field: { name: string; type: string }): JSX.Element => {
    const items = normalizeToArray(data[field.name]);
    const fieldType = cleanTypeName(field.type);
    const displayName = getFieldDisplayName(field);

    return (
      <div className={`field-block field-level-${level} repeatable-field-block`} key={field.name}>
        <div className="field-header">
          <span className="field-name">{displayName}</span>
        </div>
        {items.map((item, index) => (
          <div className="repeatable-item" key={`${field.name}-${index}`}>
            <div className="repeatable-item-header">
              <span className="repeatable-item-title">
                {t('policyBuilder.ruleN', { n: index + 1 })}
              </span>
              <button
                type="button"
                className="delete-button"
                onClick={() => handleRemoveRepeatableItem(field.name, index)}
                title={t('policyBuilder.removeRule')}
              >
                ×
              </button>
            </div>
            <PolicyBuilder
              type={fieldType}
              schema={schema}
              data={item}
              onChange={handleRepeatableItemChange(field.name, index)}
              level={level + 1}
              path={`${path}.${field.name}[${index}]`}
            />
          </div>
        ))}
        <button
          type="button"
          className="add-button"
          onClick={() => handleAddField(field.name, isComplexType(schema, fieldType), field.type)}
        >
          ➕ {t('policyBuilder.addRule')}
        </button>
      </div>
    );
  };

  const renderField = (field: { name: string; type: string }): JSX.Element => {
    const fieldValue = data[field.name];
    const isExpanded = expandedFields.has(field.name);
    const displayName = getFieldDisplayName(field);

    let fieldType = cleanTypeName(field.type);
    if (typeof fieldValue === 'object' && fieldValue && (fieldValue as Record<string, unknown>)['@xsi:type']) {
      fieldType = cleanTypeName(String((fieldValue as Record<string, unknown>)['@xsi:type']));
    }

    const isComplex = isComplexType(schema, fieldType);
    const allowDelete = !(level === 0 && field.name === 'id');

    return (
      <div className={`field-block field-level-${level}`} key={field.name}>
        <div className="field-header">
          <span className="field-name">{displayName}</span>
          {isComplex ? (
            <>
              <button
                type="button"
                className="expand-button"
                onClick={() => toggleField(field.name)}
                title={isExpanded ? t('policyBuilder.collapse') : t('policyBuilder.expand')}
              >
                {isExpanded ? '▼' : '▶'} {fieldType}
              </button>
              {allowDelete && (
                <button
                  type="button"
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
                  type="button"
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

  const addedFields = Object.keys(data).filter(
    (key) => !key.startsWith('@') && !key.startsWith('xmlns') && key !== 'xsi:schemaLocation'
  );

  const isSpecialField = (field: { name: string }): boolean =>
    isRepeatableField(field.name) || isDefaultActionField(field.name, effectiveType);

  const visibleFields = typeDef.fields.filter(
    (f) => addedFields.includes(f.name) && !isSpecialField(f)
  );

  const repeatableFieldsInUse = typeDef.fields.filter(
    (f) => isRepeatableField(f.name) && addedFields.includes(f.name)
  );

  const missingFields = typeDef.fields.filter(
    (f) => !addedFields.includes(f.name) && !isSpecialField(f)
  );

  const repeatableFieldsMissing = typeDef.fields.filter(
    (f) => isRepeatableField(f.name) && !addedFields.includes(f.name)
  );

  return (
    <div className={`policy-builder policy-level-${level}`}>
      {level === 0 && <h3 className="builder-title">{effectiveType}</h3>}

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

      {visibleFields.map(renderField)}

      {effectiveType === 'RuleSetConfiguration' && renderDefaultActionSelector()}

      {repeatableFieldsInUse.map(renderRepeatableField)}

      {(missingFields.length > 0 || repeatableFieldsMissing.length > 0 || pendingSubType) && (
        <div className={`optional-fields optional-level-${level}`}>
          {pendingSubType && (
            <div className="subtype-selector">
              <label>
                {t('policyBuilder.selectSubtype')} {cleanFieldName(pendingSubType.fieldName)}:
              </label>
              <select onChange={handleSubtypeSelect} defaultValue="">
                <option value="" disabled>
                  {t('policyBuilder.chooseOne')}
                </option>
                {subtypeOptions.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          )}
          {missingFields.map((f) => {
            const name = getFieldDisplayName(f);
            const isComplex = isComplexType(schema, f.type);
            return (
              <button
                type="button"
                className="add-button"
                key={f.name}
                onClick={() => handleAddField(f.name, isComplex, f.type)}
              >
                ➕ {t('policyBuilder.addField')} {name}
              </button>
            );
          })}
          {repeatableFieldsMissing.map((f) => {
            const name = getFieldDisplayName(f);
            const isComplex = isComplexType(schema, f.type);
            return (
              <button
                type="button"
                className="add-button"
                key={f.name}
                onClick={() => handleAddField(f.name, isComplex, f.type)}
              >
                ➕ {t('policyBuilder.addRule')} ({name})
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
