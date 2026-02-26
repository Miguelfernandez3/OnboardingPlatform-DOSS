import { useState, useEffect } from 'react';

const MOBILE_BREAKPOINT = 768;

/**
 * Hook para detectar si la pantalla es móvil
 * @param breakpoint - Ancho máximo para considerar móvil (default: 768px)
 */
export function useIsMobile(breakpoint: number = MOBILE_BREAKPOINT): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth <= breakpoint;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = (): void => {
      setIsMobile(window.innerWidth <= breakpoint);
    };

    window.addEventListener('resize', handleResize);
    // Verificar al montar
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [breakpoint]);

  return isMobile;
}

export default useIsMobile;
