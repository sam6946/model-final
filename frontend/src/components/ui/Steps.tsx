import clsx from 'clsx';
import { Check } from 'lucide-react';

/**
 * Barre de progression du formulaire de demande.
 * Le libellé « Étape X / 4 » est explicite : le visiteur sait toujours où il en
 * est, combien de temps il lui reste, et ce qu'il a déjà renseigné.
 */
export function ProgressSteps({
  steps,
  current,
  className,
}: {
  steps: string[];
  current: number;
  className?: string;
}) {
  const total = steps.length;
  const position = Math.min(current, total);
  const percent = ((position - 1) / (total - 1)) * 100;

  return (
    <div className={clsx('flex flex-col gap-3', className)}>
      <div className="flex items-baseline justify-between gap-4">
        <p className="font-display text-sm font-semibold text-k-ink">
          Étape {position} <span className="text-k-muted">/ {total}</span>
        </p>
        <p className="text-[0.8125rem] text-k-muted">{steps[position - 1]}</p>
      </div>

      <div className="relative h-1.5 rounded-full bg-k-line" role="progressbar" aria-valuemin={1} aria-valuemax={total} aria-valuenow={position} aria-label="Progression du formulaire">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-k-green transition-[width] duration-400 ease-out"
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>

      <ol className="hidden gap-2 sm:flex">
        {steps.map((label, index) => {
          const stepNumber = index + 1;
          const done = stepNumber < position;
          const active = stepNumber === position;
          return (
            <li key={label} className="flex flex-1 items-center gap-2">
              <span
                className={clsx(
                  'flex size-6 shrink-0 items-center justify-center rounded-full text-[0.6875rem] font-semibold',
                  done && 'bg-k-green text-white',
                  active && 'bg-k-blue text-white',
                  !done && !active && 'bg-k-mist text-k-muted',
                )}
                aria-hidden
              >
                {done ? <Check className="size-3.5" /> : stepNumber}
              </span>
              <span
                className={clsx(
                  'truncate text-[0.8125rem]',
                  active ? 'font-medium text-k-ink' : 'text-k-muted',
                )}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
