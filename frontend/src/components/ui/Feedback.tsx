import type { ReactNode } from 'react';
import clsx from 'clsx';
import { AlertTriangle, CheckCircle2, Info, Loader2, RefreshCw, WifiOff, XCircle } from 'lucide-react';

import { Button } from './Button';

type AlertTone = 'info' | 'success' | 'warning' | 'error';

const ALERT_STYLES: Record<AlertTone, { wrap: string; icon: ReactNode }> = {
  info: {
    wrap: 'border-k-blue-line bg-k-blue-soft/70 text-k-blue',
    icon: <Info className="size-4" aria-hidden />,
  },
  success: {
    wrap: 'border-k-green/25 bg-k-green-pale text-k-green-dark',
    icon: <CheckCircle2 className="size-4" aria-hidden />,
  },
  warning: {
    wrap: 'border-k-amber/25 bg-k-amber-pale text-k-amber',
    icon: <AlertTriangle className="size-4" aria-hidden />,
  },
  error: {
    wrap: 'border-k-red/25 bg-k-red-pale text-k-red',
    icon: <XCircle className="size-4" aria-hidden />,
  },
};

/** Message système : toujours une phrase complète, jamais un code technique. */
export function Alert({
  tone = 'info',
  title,
  children,
  action,
  className,
}: {
  tone?: AlertTone;
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const styles = ALERT_STYLES[tone];
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={clsx('flex items-start gap-3 rounded-k border px-4 py-3', styles.wrap, className)}
    >
      <span className="mt-0.5 shrink-0">{styles.icon}</span>
      <div className="flex-1 text-[0.875rem] leading-relaxed">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className={clsx(title && 'mt-0.5', 'opacity-90')}>{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-k-muted" role="status">
      <Loader2 className={clsx('size-4 animate-spin', className)} aria-hidden />
      {label ? <span className="text-[0.875rem]">{label}</span> : null}
    </span>
  );
}

/** Squelette de chargement : reprend la forme du contenu attendu. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('animate-pulse rounded-k bg-k-line/70', className)} aria-hidden />;
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="k-card p-5">
      <Skeleton className="h-4 w-1/3" />
      <div className="mt-4 space-y-2.5">
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton key={index} className={clsx('h-3', index % 2 === 0 ? 'w-full' : 'w-4/5')} />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-k-lg border border-dashed border-k-line bg-k-mist/60 px-6 py-10 text-center">
      {icon ? <span className="text-k-blue/70">{icon}</span> : null}
      <div className="space-y-1">
        <p className="font-display text-base font-semibold text-k-ink">{title}</p>
        {description ? <p className="mx-auto max-w-md text-[0.875rem] text-k-muted">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  offline,
}: {
  message: string;
  onRetry?: () => void;
  offline?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-k-lg border border-k-red/20 bg-k-red-pale/60 px-6 py-8 text-center">
      <span className="text-k-red">{offline ? <WifiOff className="size-5" aria-hidden /> : <AlertTriangle className="size-5" aria-hidden />}</span>
      <p className="max-w-md text-[0.875rem] text-k-ink">{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} icon={<RefreshCw className="size-3.5" aria-hidden />}>
          Réessayer
        </Button>
      ) : null}
    </div>
  );
}

/** Bandeau hors-ligne : la PWA reste utilisable sur un chantier sans réseau. */
export function OfflineBanner() {
  return (
    <div className="flex items-center justify-center gap-2 bg-k-amber px-4 py-2 text-[0.8125rem] font-medium text-white">
      <WifiOff className="size-4" aria-hidden />
      Vous êtes hors ligne : vos saisies sont conservées et seront synchronisées au retour du réseau.
    </div>
  );
}
