/**
 * Configuración y utilidades para el PolicyBuilder visual MSPL
 */

import { cleanFieldName } from './schemaUtils';

/** Campos del schema que admiten múltiples instancias en el builder */
export const REPEATABLE_FIELD_NAMES = new Set(['configurationRule']);

/** Opciones para defaultAction en RuleSetConfiguration */
export const DEFAULT_ACTION_OPTIONS = ['', 'deny', 'allow', 'reject'] as const;

export type DefaultActionValue = (typeof DEFAULT_ACTION_OPTIONS)[number];

const RULE_SET_FIELD_LABELS: Record<string, string> = {
  capability: 'capability',
  Name: 'ruleSetName',
};

export function isRepeatableField(fieldName: string): boolean {
  return REPEATABLE_FIELD_NAMES.has(cleanFieldName(fieldName));
}

export function normalizeToArray(value: unknown): Record<string, unknown>[] {
  if (value === null || value === undefined) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.filter(
      (item): item is Record<string, unknown> =>
        typeof item === 'object' && item !== null && !Array.isArray(item)
    );
  }
  if (typeof value === 'object') {
    return [value as Record<string, unknown>];
  }
  return [];
}

export function getRuleSetFieldLabelKey(fieldName: string): string | undefined {
  return RULE_SET_FIELD_LABELS[cleanFieldName(fieldName)];
}

const FILTERING_ACTION_TYPE_KEYS = new Set([
  'FilteringActionType',
  '{http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd}FilteringActionType',
]);

function readFilteringActionType(obj: Record<string, unknown>): string {
  for (const [key, value] of Object.entries(obj)) {
    if (FILTERING_ACTION_TYPE_KEYS.has(key) || cleanFieldName(key) === 'FilteringActionType') {
      return String(value ?? '').trim();
    }
  }
  return '';
}

/**
 * Extrae defaultAction como string desde valor plano o objeto FilteringAction anidado.
 */
export function readDefaultActionValue(value: unknown): DefaultActionValue {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (DEFAULT_ACTION_OPTIONS.includes(normalized as DefaultActionValue)) {
      return normalized as DefaultActionValue;
    }
    return '';
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    const obj = value as Record<string, unknown>;
    const direct = readFilteringActionType(obj);
    if (direct) {
      const normalized = direct.toLowerCase();
      if (DEFAULT_ACTION_OPTIONS.includes(normalized as DefaultActionValue)) {
        return normalized as DefaultActionValue;
      }
    }
    for (const nested of Object.values(obj)) {
      if (typeof nested === 'object' && nested !== null && !Array.isArray(nested)) {
        const fromNested = readFilteringActionType(nested as Record<string, unknown>);
        if (fromNested) {
          const normalized = fromNested.toLowerCase();
          if (DEFAULT_ACTION_OPTIONS.includes(normalized as DefaultActionValue)) {
            return normalized as DefaultActionValue;
          }
        }
      }
    }
  }
  return '';
}

export function isDefaultActionField(fieldName: string, parentType: string): boolean {
  return parentType === 'RuleSetConfiguration' && cleanFieldName(fieldName) === 'defaultAction';
}

export function createEmptyConfigurationRule(): Record<string, unknown> {
  return {};
}
