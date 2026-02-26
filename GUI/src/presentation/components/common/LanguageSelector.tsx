import { useTranslation } from 'react-i18next';

/**
 * LanguageSelector - Componente para cambiar el idioma
 */
export default function LanguageSelector(): JSX.Element {
  const { i18n } = useTranslation();

  const changeLanguage = (lng: string): void => {
    i18n.changeLanguage(lng);
  };

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
      <button
        onClick={() => changeLanguage('en')}
        style={{
          padding: '0.5rem 1rem',
          backgroundColor: i18n.language === 'en' || i18n.language.startsWith('en') ? '#007bff' : 'transparent',
          color: 'white',
          border: '1px solid white',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.875rem',
          fontWeight: i18n.language === 'en' || i18n.language.startsWith('en') ? 'bold' : 'normal'
        }}
      >
        EN
      </button>
      <button
        onClick={() => changeLanguage('es')}
        style={{
          padding: '0.5rem 1rem',
          backgroundColor: i18n.language === 'es' || i18n.language.startsWith('es') ? '#007bff' : 'transparent',
          color: 'white',
          border: '1px solid white',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.875rem',
          fontWeight: i18n.language === 'es' || i18n.language.startsWith('es') ? 'bold' : 'normal'
        }}
      >
        ES
      </button>
    </div>
  );
}

