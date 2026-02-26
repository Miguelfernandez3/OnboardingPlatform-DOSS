/**
 * Utilidades para trabajar con el schema MSPL
 */

const MSPL_NAMESPACE = 'http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd';

export interface SchemaType {
  base_type?: string;
  fields: Array<{ name: string; type: string }>;
}

export interface Schema {
  type_tree: Record<string, SchemaType>;
}

/**
 * Limpia el nombre de un campo removiendo el namespace
 * Ejemplo: "{http://...}ITResource" -> "ITResource"
 */
export function cleanFieldName(name: string): string {
  if (name.includes('}')) {
    return name.split('}')[1];
  }
  return name;
}

/**
 * Limpia el nombre de un tipo removiendo el namespace
 * Ejemplo: "{http://...}ITResourceType" -> "ITResourceType"
 */
export function cleanTypeName(type: string): string {
  if (type.includes('}')) {
    return type.split('}')[1];
  }
  return type;
}

/**
 * Obtiene el nombre completo de un campo con namespace
 */
export function getFullFieldName(fieldName: string): string {
  if (fieldName.startsWith('{')) {
    return fieldName;
  }
  return `{${MSPL_NAMESPACE}}${fieldName}`;
}

/**
 * Obtiene todos los subtipos de un tipo base
 */
export function getSubtypes(schema: Schema, baseType: string): string[] {
  const cleanBase = cleanTypeName(baseType);
  return Object.keys(schema.type_tree)
    .filter((type) => {
      const typeDef = schema.type_tree[type];
      return typeDef.base_type && cleanTypeName(typeDef.base_type) === cleanBase;
    })
    .sort();
}

/**
 * Verifica si un tipo es complejo (tiene definición en el schema)
 */
export function isComplexType(schema: Schema, type: string): boolean {
  const cleanType = cleanTypeName(type);
  return !!schema.type_tree[cleanType];
}

/**
 * Obtiene la definición de un tipo del schema
 */
export function getTypeDefinition(schema: Schema, type: string): SchemaType | undefined {
  const cleanType = cleanTypeName(type);
  return schema.type_tree[cleanType];
}

/**
 * Obtiene el tipo efectivo considerando xsi:type si existe
 */
export function getEffectiveType(
  baseType: string,
  data: Record<string, unknown>
): string {
  if (data && data['@xsi:type']) {
    return cleanTypeName(String(data['@xsi:type']));
  }
  return cleanTypeName(baseType);
}
