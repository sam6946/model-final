import { useEffect, useRef, useState } from 'react';

/**
 * Apparition discrète au défilement.
 * Une seule animation par élément, jouée une fois, désactivée si l'utilisateur
 * a demandé à réduire les mouvements (voir `prefers-reduced-motion` dans le CSS).
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: { threshold?: number }) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      node.dataset.visible = 'true';
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).dataset.visible = 'true';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: options?.threshold ?? 0.14, rootMargin: '0px 0px -40px 0px' },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [options?.threshold]);

  return ref;
}

/** Détecte la présence réseau pour adapter l'interface (usage chantier, 3G instable). */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine));

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []);

  return online;
}
