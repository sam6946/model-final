import clsx from 'clsx';

/**
 * Marque KEMTA.
 *
 * Le symbole reprend une trame de ferraillage (barres croisées) contenue dans
 * un carré : le suivi, la structure, la solidité — sans immeuble générique ni
 * dégradé multicolore. Le vert signale la preuve terrain, le bleu l'institution.
 */
export function BrandMark({ className, tone = 'blue' }: { className?: string; tone?: 'blue' | 'white' }) {
  const square = tone === 'white' ? '#ffffff' : '#063b5c';
  const accent = tone === 'white' ? '#3ddc7f' : '#20a04b';
  return (
    <svg
      viewBox="0 0 32 32"
      className={clsx('size-8', className)}
      role="img"
      aria-label="KEMTA"
      focusable="false"
    >
      <rect x="1.5" y="1.5" width="29" height="29" rx="7" fill={square} />
      <path d="M8 23V9" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M8 16.2 14.6 9.6" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M8.6 15.6 15.4 23" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M18.5 9.5h7.2M18.5 16h5.2M18.5 22.5h7.2" stroke={accent} strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function BrandWordmark({
  className,
  tone = 'blue',
  compact = false,
}: {
  className?: string;
  tone?: 'blue' | 'white';
  compact?: boolean;
}) {
  return (
    <span className={clsx('inline-flex items-center gap-2.5', className)}>
      <BrandMark tone={tone} className={compact ? 'size-7' : 'size-8'} />
      <span className="flex flex-col leading-none">
        <span
          className={clsx(
            'font-display font-bold tracking-[0.16em]',
            compact ? 'text-base' : 'text-lg',
            tone === 'white' ? 'text-white' : 'text-k-blue',
          )}
        >
          KEMTA
        </span>
        {!compact ? (
          <span
            className={clsx(
              'mt-1 text-[0.5625rem] font-medium uppercase tracking-[0.18em]',
              tone === 'white' ? 'text-white/70' : 'text-k-muted',
            )}
          >
            Suivi de chantier · Cameroun
          </span>
        ) : null}
      </span>
    </span>
  );
}
