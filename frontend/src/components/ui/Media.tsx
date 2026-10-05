import { useState } from 'react';
import clsx from 'clsx';

/**
 * Image responsive du site.
 *
 * La direction photographique du site est documentaire : chantiers réels,
 * lumière naturelle, visages camerounais. Chaque visuel est décliné en trois
 * largeurs (640 / 960 / 1440) pour qu'un téléphone en 3G ne télécharge jamais
 * l'image du grand écran. Si un fichier n'est pas encore disponible, on affiche
 * un aplat de marque : jamais d'image cassée, jamais de contenu de remplissage.
 */
export type MediaName =
  | 'hero-suivi-chantier'
  | 'preuve-terrain'
  | 'villa-livree'
  | 'suivi-diaspora'
  | 'materiaux-chantier'
  | 'inspection-propriete'
  | 'equipe-btp'
  | 'entretien-toiture'
  | 'marche-btp'
  | 'controle-financier';

export function Media({
  name,
  alt,
  className,
  imgClassName,
  width = 1200,
  sizes = '(min-width: 1024px) 50vw, 100vw',
  priority = false,
  ratio = '4 / 3',
}: {
  name: MediaName;
  alt: string;
  className?: string;
  imgClassName?: string;
  width?: number;
  sizes?: string;
  priority?: boolean;
  ratio?: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div
      className={clsx('relative overflow-hidden rounded-k-lg bg-k-blue-soft', className)}
      style={{ aspectRatio: ratio }}
    >
      {failed ? (
        <div
          className="k-grid-lines absolute inset-0 flex items-end bg-k-blue p-6"
          role="img"
          aria-label={alt}
        >
          <span className="max-w-[22ch] font-display text-sm font-medium leading-snug text-white/85">
            {alt}
          </span>
        </div>
      ) : (
        <picture>
          <source
            type="image/webp"
            sizes={sizes}
            srcSet={[640, 960, 1440].map((w) => `/images/${name}-${w}.webp ${w}w`).join(', ')}
          />
          <img
            src={`/images/${name}-${width}.jpg`}
            alt={alt}
            loading={priority ? 'eager' : 'lazy'}
            decoding={priority ? 'sync' : 'async'}
            fetchPriority={priority ? 'high' : 'auto'}
            onError={() => setFailed(true)}
            className={clsx('absolute inset-0 size-full object-cover', imgClassName)}
          />
        </picture>
      )}
    </div>
  );
}

/**
 * Capture d'écran d'interface : composé en HTML/CSS plutôt qu'en image, pour
 * rester net sur tous les écrans et se mettre à jour avec le produit.
 */
export function InterfaceFrame({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx('overflow-hidden rounded-k-xl border border-k-line bg-white shadow-k-lg', className)}>
      <div className="flex items-center gap-2 border-b border-k-line bg-k-mist/80 px-4 py-2.5">
        <span className="flex gap-1.5" aria-hidden>
          <span className="size-2.5 rounded-full bg-k-line" />
          <span className="size-2.5 rounded-full bg-k-line" />
          <span className="size-2.5 rounded-full bg-k-line" />
        </span>
        <div className="ml-2 min-w-0">
          <p className="truncate text-[0.75rem] font-medium text-k-ink">{title}</p>
          {subtitle ? <p className="truncate text-[0.6875rem] text-k-muted">{subtitle}</p> : null}
        </div>
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </div>
  );
}
