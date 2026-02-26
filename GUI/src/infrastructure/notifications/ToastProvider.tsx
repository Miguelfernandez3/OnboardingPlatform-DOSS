import { Toaster } from 'react-hot-toast';
import { toastConfig } from './toastConfig';

/**
 * Provider de Toast Notifications
 * Debe envolver la aplicación en App.tsx
 */
export function ToastProvider() {
  return <Toaster {...toastConfig} />;
}
