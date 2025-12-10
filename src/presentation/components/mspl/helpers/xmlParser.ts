/**
 * Parser XML a JSON para MSPL
 * Convierte XML a formato compatible con el schema MSPL
 */

import { XMLParser } from 'fast-xml-parser';

const MSPL_NAMESPACE = 'http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd';
const XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance';

interface ParseOptions {
  ignoreAttributes?: boolean;
  attributeNamePrefix?: string;
  textNodeName?: string;
  ignoreNameSpace?: boolean;
  parseAttributeValue?: boolean;
  parseNodeValue?: boolean;
  trimValues?: boolean;
}

/**
 * Convierte un objeto parseado de fast-xml-parser al formato esperado por el schema
 */
function normalizeParsedObject(obj: unknown, parentKey?: string): unknown {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => normalizeParsedObject(item));
  }

  const normalized: Record<string, unknown> = {};
  const entries = Object.entries(obj as Record<string, unknown>);

  for (const [key, value] of entries) {
    // Manejar atributos XML (fast-xml-parser usa @_ como prefijo)
    if (key.startsWith('@_')) {
      const attrName = key.substring(2);
      // Atributos especiales del elemento raíz
      if (attrName === 'id' || attrName === 'orchestrationID' || attrName === 'tenantID' || attrName === 'sliceID') {
        normalized[attrName] = value;
      } else if (attrName.startsWith('xsi:')) {
        // Atributos xsi:type se guardan con @
        normalized[`@${attrName}`] = value;
      } else {
        // Otros atributos también con @
        normalized[`@${attrName}`] = value;
      }
      continue;
    }

    // Manejar texto directo
    if (key === '#text') {
      // Si solo hay texto, retornarlo directamente
      if (parentKey && Object.keys(obj as Record<string, unknown>).length === 1) {
        return value;
      }
      // Si hay otros campos además del texto, ignorar el texto
      continue;
    }

    // Limpiar namespace de las claves (puede venir como "ITResource:ITResource" o solo "ITResource")
    let cleanKey = key;
    if (key.includes(':')) {
      const parts = key.split(':');
      cleanKey = parts[parts.length - 1];
    }

    // Agregar namespace completo para campos del schema
    const fullKey = `{${MSPL_NAMESPACE}}${cleanKey}`;

    // Normalizar el valor
    const normalizedValue = normalizeParsedObject(value, cleanKey);

    // Si el valor es un objeto simple con solo texto, usar el texto directamente
    if (
      typeof normalizedValue === 'object' &&
      normalizedValue !== null &&
      !Array.isArray(normalizedValue) &&
      Object.keys(normalizedValue).length === 1 &&
      '#text' in normalizedValue
    ) {
      normalized[fullKey] = (normalizedValue as Record<string, unknown>)['#text'];
    } else if (
      typeof normalizedValue === 'object' &&
      normalizedValue !== null &&
      !Array.isArray(normalizedValue) &&
      Object.keys(normalizedValue).length === 0
    ) {
      // Objeto vacío
      normalized[fullKey] = {};
    } else {
      normalized[fullKey] = normalizedValue;
    }
  }

  return normalized;
}

/**
 * Parsea XML string a objeto JSON compatible con el schema MSPL
 */
export function parseXmlToObject(xmlString: string): Record<string, unknown> {
  const parserOptions: ParseOptions = {
    ignoreAttributes: false,
    attributeNamePrefix: '@_',
    textNodeName: '#text',
    ignoreNameSpace: false,
    parseAttributeValue: true,
    parseNodeValue: true,
    trimValues: true,
  };

  const parser = new XMLParser(parserOptions);
  const parsed = parser.parse(xmlString);

  // Extraer el elemento raíz (ITResourceOrchestration o ITResource)
  const rootKey = Object.keys(parsed)[0];
  const rootData = parsed[rootKey];

  // Normalizar el objeto parseado
  let normalized = normalizeParsedObject(rootData, rootKey) as Record<string, unknown>;

  // Si el resultado es un string (solo texto), crear un objeto
  if (typeof normalized === 'string') {
    normalized = { '#text': normalized };
  }

  // Asegurar que el id esté en el nivel superior si existe en atributos
  if (rootData && typeof rootData === 'object' && '@_id' in rootData) {
    normalized.id = (rootData as Record<string, unknown>)['@_id'];
  }

  // Asegurar namespaces XML si no existen
  if (!normalized.xmlns) {
    normalized.xmlns = MSPL_NAMESPACE;
  }
  if (!normalized['xmlns:xsi']) {
    normalized['xmlns:xsi'] = XSI_NAMESPACE;
  }
  if (!normalized['xsi:schemaLocation']) {
    normalized['xsi:schemaLocation'] = `${MSPL_NAMESPACE} mspl.xsd`;
  }

  return normalized;
}

/**
 * Valida que el XML tenga la estructura básica correcta
 */
export function validateMSPLXml(xmlString: string): { valid: boolean; error?: string } {
  if (!xmlString || typeof xmlString !== 'string') {
    return { valid: false, error: 'XML debe ser una cadena de texto' };
  }

  if (!xmlString.includes('<ITResourceOrchestration') && !xmlString.includes('<ITResource')) {
    return { valid: false, error: 'XML debe contener ITResourceOrchestration o ITResource' };
  }

  try {
    parseXmlToObject(xmlString);
    return { valid: true };
  } catch (error) {
    return {
      valid: false,
      error: `Error al parsear XML: ${error instanceof Error ? error.message : 'Error desconocido'}`,
    };
  }
}
