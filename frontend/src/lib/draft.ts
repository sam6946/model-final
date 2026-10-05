/**
 * Brouillons de formulaire conservés dans le navigateur.
 *
 * Un client camerounais qui remplit une demande de construction depuis son
 * téléphone perd souvent la connexion en cours de route : la saisie doit
 * survivre à un rafraîchissement, à une coupure réseau ou à une fermeture
 * d'onglet. Les données restent **locales** (aucun envoi tant que le client
 * n'a pas validé), et expirent au bout de 72 heures pour ne pas laisser de
 * données personnelles dormir indéfiniment sur un téléphone partagé.
 */

const PREFIX = 'kemta.draft.';
const TTL_MS = 72 * 3600 * 1000;

type Envelope<T> = { savedAt: number; data: T };

export function saveDraft<T>(key: string, data: T): void {
  try {
    const envelope: Envelope<T> = { savedAt: Date.now(), data };
    localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(envelope));
  } catch {
    // Quota dépassé ou navigation privée : on n'interrompt jamais la saisie.
  }
}

export function loadDraft<T>(key: string): { data: T; savedAt: number } | null {
  try {
    const raw = localStorage.getItem(`${PREFIX}${key}`);
    if (!raw) return null;
    const envelope = JSON.parse(raw) as Envelope<T>;
    if (!envelope?.savedAt || Date.now() - envelope.savedAt > TTL_MS) {
      localStorage.removeItem(`${PREFIX}${key}`);
      return null;
    }
    return { data: envelope.data, savedAt: envelope.savedAt };
  } catch {
    return null;
  }
}

export function clearDraft(key: string): void {
  try {
    localStorage.removeItem(`${PREFIX}${key}`);
  } catch {
    /* ignoré */
  }
}

/** Écriture différée : évite de toucher au stockage à chaque frappe. */
export function debounce<T extends (...args: never[]) => void>(fn: T, delay = 400): T {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return ((...args: never[]) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  }) as T;
}
