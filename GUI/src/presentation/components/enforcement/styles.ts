import { CSSProperties } from 'react';

export const card: CSSProperties = {
  backgroundColor: '#fff',
  borderRadius: '8px',
  border: '1px solid #dee2e6',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  padding: '1.5rem',
};

export const tableWrapper: CSSProperties = {
  overflowX: 'auto',
  WebkitOverflowScrolling: 'touch',
};

export const table: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  minWidth: '700px',
};

export const thead: CSSProperties = {
  backgroundColor: '#f8f9fa',
  borderBottom: '2px solid #dee2e6',
};

export const th: CSSProperties = {
  padding: '0.75rem',
  textAlign: 'left',
  whiteSpace: 'nowrap',
};

export const td: CSSProperties = {
  padding: '0.75rem',
};

export const tr: CSSProperties = {
  borderBottom: '1px solid #dee2e6',
};

export const input: CSSProperties = {
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid #dee2e6',
  fontSize: '0.875rem',
  width: '100%',
  boxSizing: 'border-box',
};

export const select: CSSProperties = {
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid #dee2e6',
  fontSize: '0.875rem',
  width: '100%',
  boxSizing: 'border-box',
  backgroundColor: 'white',
};

export const textarea: CSSProperties = {
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid #dee2e6',
  fontSize: '0.875rem',
  width: '100%',
  boxSizing: 'border-box',
  minHeight: '100px',
  fontFamily: 'monospace',
};

export const formGrid: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '0.75rem',
};

export const checkboxRow: CSSProperties = {
  display: 'flex',
  gap: '1rem',
  flexWrap: 'wrap',
  marginTop: '0.75rem',
  alignItems: 'center',
};

export const checkboxLabel: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.375rem',
  fontSize: '0.875rem',
  cursor: 'pointer',
};

export const btnPrimary: CSSProperties = {
  padding: '0.5rem 1rem',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
};

export const btnSuccess: CSSProperties = {
  padding: '0.5rem 1rem',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
};

export const btnDanger: CSSProperties = {
  padding: '0.375rem 0.75rem',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.875rem',
};

export const btnSecondary: CSSProperties = {
  padding: '0.5rem 1rem',
  backgroundColor: 'white',
  color: '#6c757d',
  border: '1px solid #dee2e6',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.875rem',
};

export const btnWarning: CSSProperties = {
  padding: '0.375rem 0.75rem',
  backgroundColor: '#ffc107',
  color: '#212529',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.875rem',
};

export const badgeActive: CSSProperties = {
  padding: '0.25rem 0.5rem',
  borderRadius: '4px',
  backgroundColor: '#d4edda',
  color: '#155724',
  fontSize: '0.75rem',
  fontWeight: 500,
};

export const badgeInactive: CSSProperties = {
  padding: '0.25rem 0.5rem',
  borderRadius: '4px',
  backgroundColor: '#fff3cd',
  color: '#856404',
  fontSize: '0.75rem',
  fontWeight: 500,
};

export const badgeSuccess: CSSProperties = {
  padding: '0.25rem 0.5rem',
  borderRadius: '4px',
  backgroundColor: '#d4edda',
  color: '#155724',
  fontSize: '0.75rem',
  fontWeight: 500,
};

export const badgeError: CSSProperties = {
  padding: '0.25rem 0.5rem',
  borderRadius: '4px',
  backgroundColor: '#f8d7da',
  color: '#721c24',
  fontSize: '0.75rem',
  fontWeight: 500,
};

export const mobileCard: CSSProperties = {
  padding: '1rem',
  backgroundColor: '#fff',
  borderRadius: '8px',
  border: '1px solid #dee2e6',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

export const mobileCardField: CSSProperties = {
  fontSize: '0.875rem',
  color: '#666',
  marginBottom: '0.25rem',
};

export const buttonRow: CSSProperties = {
  display: 'flex',
  gap: '0.5rem',
  marginTop: '0.75rem',
};

export const formLabel: CSSProperties = {
  fontSize: '0.75rem',
  color: '#6c757d',
  marginBottom: '0.25rem',
  fontWeight: 500,
};

export const formSection: CSSProperties = {
  marginBottom: '1.5rem',
};

export const formSectionTitle: CSSProperties = {
  fontSize: '0.875rem',
  fontWeight: 600,
  color: '#495057',
  marginBottom: '0.75rem',
  paddingBottom: '0.375rem',
  borderBottom: '1px solid #e9ecef',
};

/** Subtítulo dentro de una sección (p. ej. contexto vs auth en el mismo bloque). */
export const formSubsectionTitle: CSSProperties = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: '#495057',
  marginBottom: '0.5rem',
};

/** Agrupa context_spec + auth + opciones Bearer en un solo panel. */
export const mergedContextAuthPanel: CSSProperties = {
  border: '1px solid #e9ecef',
  borderRadius: '8px',
  padding: '1rem',
  backgroundColor: '#f8f9fa',
  display: 'flex',
  flexDirection: 'column',
  gap: '1.25rem',
};

export const mergedContextAuthDivider: CSSProperties = {
  borderTop: '1px solid #dee2e6',
  paddingTop: '1.25rem',
  marginTop: 0,
};

export const bearerStrategySummary: CSSProperties = {
  fontSize: '0.8125rem',
  lineHeight: 1.45,
  margin: 0,
  padding: '0.5rem 0.75rem',
  borderRadius: '6px',
  border: '1px solid transparent',
};

export const sectionIntroMuted: CSSProperties = {
  fontSize: '0.8125rem',
  color: '#6c757d',
  lineHeight: 1.45,
  margin: '0 0 0.75rem 0',
};

export const formRow: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: '0.75rem',
  marginBottom: '0.75rem',
};

export const formFieldFull: CSSProperties = {
  gridColumn: '1 / -1',
};

/** Sección Auth: campos apilados para evitar columnas desbalanceadas (aviso + select). */
export const authSectionStack: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '1.25rem',
};

export const authFieldColumn: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.5rem',
};

export const authSecretColumn: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.75rem',
};

export const authInfoBanner: CSSProperties = {
  fontSize: '0.875rem',
  color: '#0c5460',
  margin: 0,
  padding: '0.75rem 0.875rem',
  backgroundColor: '#d1ecf1',
  border: '1px solid #bee5eb',
  borderRadius: '6px',
  lineHeight: 1.5,
};

export const authWarningBanner: CSSProperties = {
  fontSize: '0.875rem',
  color: '#856404',
  margin: 0,
  padding: '0.75rem 0.875rem',
  backgroundColor: '#fff3cd',
  border: '1px solid #ffeaa7',
  borderRadius: '6px',
  lineHeight: 1.5,
};

export const optionsCard: CSSProperties = {
  padding: '1rem',
  backgroundColor: '#f8f9fa',
  borderRadius: '6px',
  border: '1px solid #e9ecef',
};

export const optionItem: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-start',
  gap: '0.125rem',
  marginBottom: '0.75rem',
};

export const optionLabel: CSSProperties = {
  fontSize: '0.875rem',
  cursor: 'pointer',
  flex: 1,
};

export const optionHint: CSSProperties = {
  fontSize: '0.75rem',
  color: '#6c757d',
  marginLeft: '1.5rem',
};

export const optionHintFlush: CSSProperties = {
  ...optionHint,
  marginLeft: 0,
};

/** Tabla de requisitos (context spec): ancho completo del contenedor, columnas proporcionales. */
export const contextSpecTableWrap: CSSProperties = {
  border: '1px solid #dee2e6',
  borderRadius: '6px',
  overflowX: 'auto',
  width: '100%',
  maxWidth: '100%',
  boxSizing: 'border-box',
};

export const contextSpecTable: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.875rem',
  tableLayout: 'fixed',
};

export const contextSpecTh: CSSProperties = {
  padding: '0.5rem 0.625rem',
  fontWeight: 600,
  fontSize: '0.75rem',
  color: '#495057',
  backgroundColor: '#f8f9fa',
  borderBottom: '1px solid #dee2e6',
  textAlign: 'left',
  verticalAlign: 'middle',
};

export const contextSpecTd: CSSProperties = {
  padding: '0.5rem 0.625rem',
  verticalAlign: 'middle',
  borderBottom: '1px solid #eef1f3',
};

export const contextSpecRowInput: CSSProperties = {
  ...input,
  minWidth: 0,
  width: '100%',
};

export const contextReqRemoveBtn: CSSProperties = {
  padding: '0.375rem 0.625rem',
  fontSize: '0.8125rem',
  backgroundColor: '#fff',
  color: '#9b2226',
  border: '1px solid #e9a1a7',
  borderRadius: '4px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  fontWeight: 500,
};

export const contextRequirementsSection: CSSProperties = {
  marginTop: '0.75rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.625rem',
};

export const contextSpecActionsRow: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: '0.5rem',
};

export const contextSpecFooterHint: CSSProperties = {
  ...optionHintFlush,
  lineHeight: 1.45,
};

export const logDetails: CSSProperties = {
  marginTop: '0.5rem',
  border: '1px solid #e9ecef',
  borderRadius: '6px',
  backgroundColor: '#f8f9fa',
  overflow: 'hidden',
};

export const logDetailsSummary: CSSProperties = {
  cursor: 'pointer',
  padding: '0.625rem 0.75rem',
  fontSize: '0.875rem',
  fontWeight: 600,
  color: '#495057',
};

export const logDetailsSection: CSSProperties = {
  padding: '0 0.75rem 0.75rem 0.75rem',
};

export const logDetailsLabel: CSSProperties = {
  fontSize: '0.75rem',
  fontWeight: 600,
  color: '#6c757d',
  marginBottom: '0.375rem',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

export const logCodeBlock: CSSProperties = {
  margin: 0,
  padding: '0.75rem',
  backgroundColor: '#ffffff',
  border: '1px solid #dee2e6',
  borderRadius: '4px',
  fontFamily: 'SFMono-Regular, Consolas, Monaco, Menlo, monospace',
  fontSize: '0.8rem',
  lineHeight: 1.5,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  overflowX: 'auto',
};
