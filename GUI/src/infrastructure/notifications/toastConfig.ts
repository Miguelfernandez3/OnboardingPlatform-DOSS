import { ToasterProps } from 'react-hot-toast';

export const toastConfig: ToasterProps = {
  position: 'top-right',
  reverseOrder: false,
  gutter: 8,
  containerClassName: '',
  containerStyle: {},
  toastOptions: {
    // Duración por defecto según tipo
    duration: 5000,
    // Estilos base
    style: {
      background: '#363636',
      color: '#fff',
      padding: '16px',
      borderRadius: '8px',
      fontSize: '14px',
      maxWidth: '400px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    },
    // Estilos por tipo
    success: {
      duration: 4000,
      iconTheme: {
        primary: '#10b981',
        secondary: '#fff',
      },
      style: {
        background: '#10b981',
      },
    },
    error: {
      duration: 6000,
      iconTheme: {
        primary: '#ef4444',
        secondary: '#fff',
      },
      style: {
        background: '#ef4444',
      },
    },
  },
};
