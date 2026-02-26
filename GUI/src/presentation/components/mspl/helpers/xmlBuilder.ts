/**
 * Builder JSON a XML para MSPL
 * Convierte objetos JSON compatibles con el schema MSPL a XML
 */

import { create } from 'xmlbuilder2';

//const MSPL_NAMESPACE = 'http://modeliosoft/xsddesigner/a22bd60b-ee3d-425c-8618-beb6a854051a/ITResource.xsd';
//const XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance';

/**
 * Limpia el nombre de un campo removiendo el namespace
 */
function cleanFieldName(name: string): string {
  if (name.includes('}')) {
    return name.split('}')[1];
  }
  return name;
}

/**
 * Tipo para el nodo XML de xmlbuilder2
 * Se infiere del tipo de retorno de create().ele()
 */
type XMLNode = ReturnType<typeof create> & {
  att: (name: string, value: string) => XMLNode;
  ele: (name: string, attrs?: Record<string, string>) => XMLNode;
  txt: (text: string) => XMLNode;
};

/**
 * Construye XML desde un objeto JSON compatible con el schema MSPL
 * Esta función procesa recursivamente los campos del objeto, igual que en frontend-bastion
 */
function appendChildren(node: XMLNode, obj: Record<string, unknown>): void {
  Object.entries(obj).forEach(([key, value]) => {
    // Manejar atributos especiales (igual que en frontend-bastion)
    // Estos se procesan como atributos del nodo actual
    if (
      key === 'id' ||
      key === 'orchestrationID' ||
      key === 'xmlns' ||
      key === 'xmlns:xsi' ||
      key === 'xsi:schemaLocation'
    ) {
      node.att(key, String(value));
      return; // Continuar con el siguiente campo en el forEach
    }

    // Limpiar el nombre del campo (remover namespace)
    const cleanKey = cleanFieldName(key);

    // Manejar atributos XML (prefijo @)
    if (key.startsWith('@')) {
      // atributo como @xsi:type
      const attrName = key.substring(1);
      node.att(attrName, String(value));
      return;
    }

    // Manejar valores nulos, undefined o objetos vacíos
    if (
      value === null ||
      value === undefined ||
      (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0)
    ) {
      // Elemento vacío
      node.ele(cleanKey);
      return;
    }

    // Manejar objetos (igual que en frontend-bastion)
    // Nota: Array.isArray() retorna false para objetos, así que esto maneja tanto objetos como arrays
    if (typeof value === 'object' && value !== null) {
      const child = node.ele(cleanKey);
      const valueObj = value as Record<string, unknown>;

      // Añadir atributos si existen
      const valueEntries = Object.entries(valueObj);
      valueEntries.forEach(([k, v]) => {
        if (k.startsWith('@')) {
          child.att(k.substring(1), String(v));
        }
      });

      // Añadir hijos si hay (evita volver a procesar los atributos)
      const childContent = Object.fromEntries(
        valueEntries.filter(([k]) => !k.startsWith('@'))
      );
      appendChildren(child, childContent);
    } else {
      // Valor primitivo
      node.ele(cleanKey).txt(String(value));
    }
  });
}

/**
 * Construye XML desde un objeto JSON
 * @param rootTag - Tag raíz del XML (ej: "ITResourceOrchestration")
 * @param data - Objeto JSON compatible con el schema MSPL
 * @param options - Opciones adicionales
 */
export function buildXmlFromObject(
  rootTag: string,
  data: Record<string, unknown>,
  options?: { prettyPrint?: boolean; allowEmptyTags?: boolean }
): string {
  const prettyPrint = options?.prettyPrint ?? true;
  const allowEmptyTags = options?.allowEmptyTags ?? true;

  // Crear elemento raíz con id (igual que en frontend-bastion)
  // Si id existe, se pasa al crear el elemento; si no, se procesará en appendChildren
  const rootId = data.id ? String(data.id) : undefined;
  const root = create().ele(rootTag, rootId ? { id: rootId } : {});

  // Agregar hijos (appendChildren procesará todos los campos incluyendo namespaces y atributos)
  // Nota: Si id ya fue agregado al crear el root, appendChildren lo procesará de nuevo pero solo actualizará el atributo
  appendChildren(root, data);

  return root.end({ prettyPrint, allowEmptyTags });
}
