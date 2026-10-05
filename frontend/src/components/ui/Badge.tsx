import type { ReactNode } from 'react';
import clsx from 'clsx';

type Tone = 'neutral' | 'blue' | 'green' | 'amber' | 'red' | 'outline';

const TONES: Record<Tone, string> = {
  neutral: 'bg-k-mist text-k-ink border-k-line',
  blue: 'bg-k-blue-soft text-k-blue border-k-blue-line',
  green: 'bg-k-green-pale text-k-green-dark border-k-green/25',
  amber: 'bg-k-amber-pale text-k-amber border-k-amber/25',
  red: 'bg-k-red-pale text-k-red border-k-red/25',
  outline: 'bg-transparent text-k-muted border-k-line',
};

export function Badge({
  children,
  tone = 'neutral',
  size = 'md',
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  size?: 'sm' | 'md';
  className?: string;
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[0.6875rem]' : 'px-2.5 py-1 text-xs',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Badge d'état : la couleur suit le sens métier (jamais décorative). */
export function StatusBadge({ code, label }: { code?: string | null; label: string }) {
  const tone: Tone =
    ({
      COMPLETED: 'green',
      PUBLISHED: 'green',
      APPROVED: 'green',
      VERIFIED: 'green',
      ACTIVE: 'green',
      WON: 'green',
      SUCCEEDED: 'green',
      PAID: 'green',
      IN_PROGRESS: 'blue',
      OPEN: 'blue',
      PLANNING: 'blue',
      NEW: 'blue',
      REVIEWING: 'blue',
      SUBMITTED: 'blue',
      SHORTLISTED: 'blue',
      INTERVIEW: 'blue',
      CONVERTED: 'blue',
      PENDING: 'amber',
      TRIALING: 'amber',
      QUALIFYING: 'amber',
      ON_HOLD: 'amber',
      SCHEDULED: 'amber',
      PAST_DUE: 'amber',
      OVERDUE: 'amber',
      REJECTED: 'red',
      CANCELLED: 'red',
      FAILED: 'red',
      LOST: 'red',
      AWARDED: 'blue',
      ACCEPTED: 'green',
      SIGNED: 'green',
      RESOLVED: 'green',
      PUBLISHED_REALIZATION: 'green',
      DRAFT: 'neutral',
      NOT_STARTED: 'neutral',
      VACANT: 'neutral',
      UNKNOWN: 'neutral',
    } as Record<string, Tone>)[code ?? ''] ?? 'neutral';

  return (
    <Badge tone={tone}>
      <span
        className={clsx(
          'size-1.5 rounded-full',
          tone === 'green' && 'bg-k-green',
          tone === 'blue' && 'bg-k-blue',
          tone === 'amber' && 'bg-k-amber',
          tone === 'red' && 'bg-k-red',
          tone === 'neutral' && 'bg-k-muted',
        )}
        aria-hidden
      />
      {label}
    </Badge>
  );
}
