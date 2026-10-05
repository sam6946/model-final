import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <h1 className="font-display text-k-blue">KEMTA</h1>
  </StrictMode>,
);
