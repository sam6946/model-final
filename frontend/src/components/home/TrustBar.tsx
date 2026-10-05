import { usePublicContent } from '@/lib/hooks';
import { Skeleton } from '@/components/ui/Feedback';
import { Section } from '@/components/layout/Section';

/**
 * Bandeau de confiance : uniquement des chiffres vérifiables côté KEMTA
 * (nombre de chantiers suivis, entreprises contrôlées, preuves publiées).
 * Aucun logo d'entreprise fictive, aucune note inventée.
 */
export function TrustBar() {
  const { data, isLoading } = usePublicContent();
  const stats = data?.trust_stats ?? [];

  return (
    <Section tone="mist" className="!py-10 md:!py-12">
      {isLoading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>
      ) : (
        <dl className="grid gap-y-8 sm:grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-k-line">
          {stats.map((stat) => (
            <div key={stat.id} className="lg:px-6 lg:first:pl-0 lg:last:pr-0">
              <dt className="font-display text-[1.75rem] font-bold leading-none text-k-blue">
                {stat.value}
              </dt>
              <dd className="mt-2">
                <span className="block text-[0.875rem] font-medium text-k-ink">{stat.label}</span>
                <span className="mt-0.5 block text-[0.8125rem] leading-relaxed text-k-muted">
                  {stat.hint}
                </span>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Section>
  );
}
