import type { ReactNode } from 'react';
import clsx from 'clsx';

import { useReveal } from '@/hooks/useReveal';

/** Bloc de page : gère le rythme vertical et les fonds alternés. */
export function Section({
  children,
  id,
  tone = 'white',
  className,
  containerClassName,
  as: Tag = 'section',
}: {
  children: ReactNode;
  id?: string;
  tone?: 'white' | 'mist' | 'blue' | 'green';
  className?: string;
  containerClassName?: string;
  as?: 'section' | 'div';
}) {
  const tones = {
    white: 'bg-white text-k-ink',
    mist: 'bg-k-mist text-k-ink',
    blue: 'bg-k-blue text-white',
    green: 'bg-k-green-pale text-k-ink',
  } as const;

  return (
    <Tag id={id} className={clsx('k-section', tones[tone], className)}>
      <div className={clsx('k-container', containerClassName)}>{children}</div>
    </Tag>
  );
}

/** En-tête de section : surtitre court, titre utile, chapô d'une ou deux phrases. */
export function SectionHeading({
  eyebrow,
  title,
  description,
  align = 'left',
  tone = 'dark',
  action,
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  align?: 'left' | 'center';
  tone?: 'dark' | 'light';
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        'flex flex-col gap-5',
        align === 'center' && 'items-center text-center',
        action && 'md:flex-row md:items-end md:justify-between',
        className,
      )}
    >
      <div className={clsx('flex flex-col gap-3', align === 'center' && 'items-center')}>
        {eyebrow ? (
          <span className={clsx('k-eyebrow', tone === 'light' && 'text-k-green')}>{eyebrow}</span>
        ) : null}
        <h2 className={clsx(tone === 'light' && 'text-white')}>{title}</h2>
        {description ? (
          <div className={clsx('k-lead', tone === 'light' && 'text-white/75')}>{description}</div>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

/** Enveloppe d'animation au défilement (une seule fois, très discrète). */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={clsx('k-reveal', className)}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
