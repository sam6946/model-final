import { Section } from '@/components/layout/Section';
import { Skeleton } from '@/components/ui/Feedback';
import { usePublicContent } from '@/lib/hooks';
import { useReveal } from '@/hooks/useReveal';
import type { TrustStat } from '@/lib/types';

/**
 * Bandeau de confiance.
 * Les chiffres viennent du backend (`/catalog/public-content/`) : jamais de
 * statistique inventée côté front. Si l'API ne répond pas, on masque le bloc
 * plutôt que d'afficher un chiffre faux.
 */
export function TrustBar() {
  const { data, isLoading, isError } = usePublicContent();
  const ref = useReveal<HTMLDivElement>();

  const stats: TrustStat[] = data?.trust_stats ?? [];
  if (isError || (!isLoading && stats.length === 0)) return null;

  return (
    <Section tone="mist" className="!py-10 sm:!py-12">
      <div ref={ref} data-reveal className="flex flex-col gap-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-display text-[1.0625rem] font-semibold text-k-ink">
            La confiance se mesure, elle ne se promet pas.
          </p>
          <p className="max-w-[52ch] text-[0.875rem] leading-relaxed text-k-muted">
            Indicateurs consolidés par l&apos;équipe KEMTA à partir des projets réellement suivis sur la plateforme.
          </p>
        </div>

        {isLoading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="space-y-2">
                <Skeleton className="h-8 w-24" />
                <Skeleton className="h-3 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <dl className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.id} className="border-t-2 border-k-blue/15 pt-4">
                <dt className="sr-only">{stat.label}</dt>
                <dd>
                  <p className="font-display text-[1.875rem] font-bold leading-none text-k-blue sm:text-[2rem]">
                    {stat.value}
                  </p>
                  <p className="mt-2 text-[0.9375rem] font-medium text-k-ink">{stat.label}</p>
                  {stat.hint ? <p className="mt-1 text-[0.8125rem] text-k-muted">{stat.hint}</p> : null}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </Section>
  );
}
