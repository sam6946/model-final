import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';
import { AuthProvider } from '@/hooks/useAuth';
import { queryClient } from '@/lib/query';
import './styles/index.css';

const container = document.getElementById('root');
if (!container) throw new Error('Élément #root introuvable dans index.html.');

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);

/* Application installable (PWA) : équipes terrain et clients réguliers.
   Enregistré uniquement en production — le serveur de développement sert le
   service worker depuis la racine du projet Vite. */
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Un échec d'enregistrement ne doit jamais bloquer l'application :
      // le suivi de chantier reste pleinement utilisable en ligne.
    });
  });
}
