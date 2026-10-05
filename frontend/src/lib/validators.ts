/**
 * Validation des saisies, alignée sur les règles du serveur.
 *
 * Le but n'est pas de dupliquer la validation backend (qui reste la référence),
 * mais de donner au client un retour immédiat, en français, avant l'envoi.
 */

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Numéro camerounais : 9 chiffres commençant par 6, ou format international. */
export function normalizePhone(value: string): string | null {
  const raw = (value ?? '').trim();
  if (!raw) return null;

  let digits = raw.replace(/[^\d+]/g, '').replace(/^\+/, '');
  if (digits.startsWith('00')) digits = digits.slice(2);

  if (digits.startsWith('237')) digits = digits.slice(3);
  digits = digits.replace(/\D/g, '');

  if (digits.length === 9 && digits.startsWith('6')) return `+237${digits}`;
  if (digits.length === 9 && digits.startsWith('2')) return `+237${digits}`;
  if (raw.startsWith('+') && digits.length >= 8 && digits.length <= 15) return `+${digits}`;
  return null;
}

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test((value ?? '').trim());
}

export function isStrongEnoughPassword(value: string): boolean {
  return (value ?? '').length >= 8;
}

export function passwordStrength(value: string): { score: number; label: string } {
  const candidates: Array<[RegExp, number]> = [
    [/.{8,}/, 1],
    [/[a-z]/, 1],
    [/[A-Z]/, 1],
    [/\d/, 1],
    [/[^\w\s]/, 1],
  ];
  const score = candidates.reduce((total, [pattern, weight]) => (pattern.test(value) ? total + weight : total), 0);
  const labels = ['Très faible', 'Faible', 'Moyen', 'Correct', 'Solide', 'Excellent'];
  return { score, label: labels[Math.min(score, labels.length - 1)] };
}

/** Âge minimum pour créer un compte (protection des mineurs). */
export function isAdult(birthDate?: string | null): boolean {
  if (!birthDate) return true;
  const date = new Date(birthDate);
  if (Number.isNaN(date.getTime())) return true;
  const eighteenYearsAgo = new Date();
  eighteenYearsAgo.setFullYear(eighteenYearsAgo.getFullYear() - 18);
  return date <= eighteenYearsAgo;
}

/** Message d'erreur humain pour un champ vide (jamais « champ invalide »). */
export function requiredMessage(field: string): string {
  return `Veuillez renseigner ${field}.`;
}
