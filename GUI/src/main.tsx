import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './i18n/config';
import './index.css';

// Silenciar errores de extensiones del navegador en desarrollo
if (import.meta.env.DEV) {
  const originalError = console.error;
  console.error = (...args: unknown[]) => {
    // Filtrar errores de content_script.js (extensiones del navegador)
    if (args[0] && typeof args[0] === 'string' && args[0].includes('content_script.js')) {
      return;
    }
    originalError.apply(console, args);
  };

  window.addEventListener('error', (event) => {
    // Silenciar errores de extensiones del navegador
    if (event.filename && event.filename.includes('content_script.js')) {
      event.preventDefault();
      return false;
    }
  }, true);
}

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

