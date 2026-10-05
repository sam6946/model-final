/**
 * Formatage français : montants FCFA, dates, téléphones, durées.
 * Aucune dépendance externe : le rendu doit être identique côté serveur et
 * côté navigateur, et lisible par un client camerounais comme par la diaspora.
 */

const XAF = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });

/** « 25 000 000 FCFA » — séparateur insécable géré par Intl. */
export function formatXaf(value: number | string | null | undefined, options?: { compact?: boolean }): string {
  const amount = typeof value === 'string' ? Number.parseFloat(value) : (value ?? 0);
  if (!Number.isFinite(amount) || amount === 0) return options?.compact ? '0 FCFA' : '0 FCFA';
  if (options?.compact) {
    if (amount >= 1_000_000_000) return `${XAF.format(amount / 1_000_000_000)} Md FCFA`;
    if (amount >= 1_000_000) return `${XAF.format(amount / 1_000_000)} M FCFA`;
    if (amount >= 10_000) return `${XAF.format(amount / 1_000)} K FCFA`;
  }
  return `${XAF.format(amount)} FCFA`;
}

export function formatAmount(value: number | string | null | undefined): string {
  const amount = typeof value === 'string' ? Number.parseFloat(value) : (value ?? 0);
  return Number.isFinite(amount) ? XAF.format(amount) : '0';
}

const dateFormatter = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
const dateTimeFormatter = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const shortDateFormatter = new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });

export function formatDate(value?: string | Date | null): string {
  if (!value) return '—';
  const date = typeof value === 'string' ? new Date(value) : value;
  return Number.isNaN(date.getTime()) ? '—' : dateFormatter.format(date);
}

export function formatDateTime(value?: string | Date | null): string {
  if (!value) return '—';
  const date = typeof value === 'string' ? new Date(value) : value;
  return Number.isNaN(date.getTime()) ? '—' : dateTimeFormatter.format(date);
}

export function formatShortDate(value?: string | Date | null): string {
  if (!value) return '—';
  const date = typeof value === 'string' ? new Date(value) : value;
  return Number.isNaN(date.getTime()) ? '—' : shortDateFormatter.format(date);
}

/** « il y a 3 jours », « dans 2 semaines » — utile pour les échéances. */
export function relativeTime(value?: string | Date | null): string {
  if (!value) return '';
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = date.getTime() - Date.now();
  const rtf = new Intl.RelativeTimeFormat('fr-FR', { numeric: 'auto' });
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 365 * 24 * 3600 * 1000],
    ['month', 30 * 24 * 3600 * 1000],
    ['week', 7 * 24 * 3600 * 1000],
    ['day', 24 * 3600 * 1000],
    ['hour', 3600 * 1000],
    ['minute', 60 * 1000],
  ];
  for (const [unit, ms] of units) {
    if (Math.abs(diffMs) >= ms) return rtf.format(Math.round(diffMs / ms), unit);
  }
  return rtf.format(Math.round(diffMs / 1000), 'second');
}

/** « +237 6 99 11 22 33 » : affichage demandé sur les écrans côté client. */
export function formatPhone(value?: string | null): string {
  if (!value) return '';
  const digits = value.replace(/\D/g, '');
  if (digits.length === 9 && digits.startsWith('6')) {
    return `+237 ${digits[0]} ${digits.slice(1, 3)} ${digits.slice(3, 5)} ${digits.slice(5, 7)} ${digits.slice(7, 9)}`;
  }
  if (digits.length === 12 && digits.startsWith('237')) return `+237 ${digits.slice(3)}`;
  return value;
}

export function initials(name?: string | null): string {
  if (!name) return '';
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count > 1 ? `${count} ${plural ?? `${singular}s`}` : `${count} ${singular}`;
}

/** Pourcentage borné, utilisé pour les avancements et jauges. */
export function clampPercent(value: number | null | undefined): number {
  if (value === null || value === undefined || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

/** Tronque proprement un texte long sans couper un mot. */
export function truncate(text: string, max = 160): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return `${cut.slice(0, lastSpace > 0 ? lastSpace : max).trimEnd()}…`;
}

export const STATUS_LABELS: Record<string, string> = {
  NEW: 'Nouvelle',
  QUALIFYING: 'Qualification',
  QUALIFIED: 'Qualifiée',
  CONVERTED: 'Convertie en projet',
  REJECTED: 'Non retenue',
  CLOSED: 'Clôturée',
  DRAFT: 'Brouillon',
  PLANNING: 'Préparation',
  IN_PROGRESS: 'En cours',
  ON_HOLD: 'En pause',
  COMPLETED: 'Réceptionné',
  CANCELLED: 'Annulé',
  PENDING: 'En attente',
  APPROVED: 'Validé',
  PUBLISHED: 'Publié',
  ARCHIVED: 'Archivé',
  OPEN: 'Ouvert',
  REVIEWING: 'Instruction',
  AWARDED: 'Attribué',
  SUBMITTED: 'Reçue',
  SHORTLISTED: 'Présélectionnée',
  INTERVIEW: 'Entretien',
  WON: 'Sélectionnée',
  LOST: 'Écartée',
  SCHEDULED: 'Planifiée',
  CONFIRMED: 'Confirmée',
  VERIFIED: 'Vérifiée',
  ACTIVE: 'Actif',
  TRIALING: "Période d'essai",
  PAST_DUE: 'En retard',
  FAILED: 'Échoué',
  SUCCEEDED: 'Encaissé',
  PAID: 'Payée',
  OVERDUE: 'Échue',
  SUSPENDED: 'Suspendue',
  NOT_STARTED: 'Non démarrée',
  BLOCKED: 'Bloquée',
  VACANT: 'Inoccupée',
  OCCUPIED_OWNER: 'Occupée par le propriétaire',
  RENTED: 'Louée',
  FAMILY: 'Occupée par la famille',
  GUARDED: 'Gardien sur place',
  UNKNOWN: 'À préciser',
  INSPECTION: 'Inspection',
  MONTHLY: 'Mensuelle',
  QUARTERLY: 'Trimestrielle',
  SEMIANNUAL: 'Semestrielle',
  ANNUAL: 'Annuelle',
  PUNCTUAL: 'Ponctuelle',
  ON_DEMAND: 'À la demande',
  EQUIPMENT: 'Équipements',
  TECHNIQUE: 'Technique',
  MANAGER: 'Gestionnaire',
  OWNER: 'Propriétaire',
  EDITOR: 'Éditeur',
  FIELD: 'Agent terrain',
  VIEWER: 'Lecture seule',
  CLIENT: 'Client',
  COMPANY: 'Entreprise',
  ADMIN: 'Administrateur KEMTA',
  BUILD: 'Construction neuve',
  FOLLOW_UP: 'Suivi de chantier',
  MAINTENANCE: 'Entretien de propriété',
  CUSTOMER: 'Client',
  TEAM: 'Équipe KEMTA',
  PUBLIC: 'Public',
  WAITING: 'En attente',
  DONE: 'Terminée',
  DELIVERED: 'Livrée',
  DISPUTED: 'En litige',
  CANCELLED_BY_CLIENT: 'Annulée par le client',
  EXPIRED: 'Expiré',
  AWAITING_PAYMENT: 'En attente de paiement',
};

export function statusLabel(code?: string | null): string {
  if (!code) return '—';
  return STATUS_LABELS[code] ?? code.replace(/_/g, ' ').toLowerCase();
}
