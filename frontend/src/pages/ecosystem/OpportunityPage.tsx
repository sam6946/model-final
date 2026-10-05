import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BadgeCheck,
  CalendarClock,
  ChevronRight,
  Clock,
  FileText,
  HelpCircle,
  MapPin,
  Send,
  ShieldCheck,
  Wallet,
} from 'lucide-react';

import { ApiError, http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Alert, CardSkeleton, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Checkbox, Field, Input, Textarea } from '@/components/ui/Field';
import { useAuth } from '@/hooks/useAuth';
import { formatDate, formatXaf } from '@/lib/format';
import { breadcrumbSchema } from '@/lib/seo';
import type { Opportunity } from '@/lib/types';

type FormState = {
  presentation: string;
  similar_experience: string;
  methodology: string;
  estimated_budget_xaf: string;
  proposed_duration_days: string;
  team_size: string;
  team_composition: string;
  accepts_site_visit: boolean;
};

const EMPTY: FormState = {
  presentation: '',
  similar_experience: '',
  methodology: '',
  estimated_budget_xaf: '',
  proposed_duration_days: '',
  team_size: '',
  team_composition: '',
  accepts_site_visit: true,
};

export default function OpportunityPage() {
  const { slug } = useParams<{ slug: string }>();
  const queryClient = useQueryClient();
  const { isAuthenticated, spaces } = useAuth();

  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery<Opportunity>({
    queryKey: ['opportunity', slug],
    enabled: Boolean(slug),
    queryFn: () => http.get<Opportunity>(`/opportunities/${slug}/`),
    staleTime: 60_000,
  });

  const isCompanyUser = spaces.some((space) => space.key === 'company' && space.available);

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      http.post<{ reference: string; message: string }>(`/opportunities/${slug}/apply/`, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['opportunity', slug] });
      void queryClient.invalidateQueries({ queryKey: ['applications', 'mine'] });
    },
  });

  if (isError) {
    return (
      <Section>
        <ErrorState message="Ce marché n'a pas pu être chargé : il a peut-être été clôturé." onRetry={() => void refetch()} />
        <div className="mt-6 text-center">
          <ButtonLink to="/opportunites" variant="secondary">
            Revenir aux marchés
          </ButtonLink>
        </div>
      </Section>
    );
  }

  if (isLoading || !data) {
    return (
      <Section>
        <CardSkeleton lines={8} />
      </Section>
    );
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);

    const next: Record<string, string> = {};
    if (form.presentation.trim().length < 80) {
      next.presentation =
        'Détaillez votre présentation (80 caractères minimum) : c\'est le premier critère analysé par le client.';
    }
    if (form.estimated_budget_xaf && Number(form.estimated_budget_xaf) <= 0) {
      next.estimated_budget_xaf = 'Indiquez un montant en francs CFA, ou laissez le champ vide.';
    }
    if (form.proposed_duration_days && Number(form.proposed_duration_days) <= 0) {
      next.proposed_duration_days = 'Indiquez une durée en jours, ou laissez le champ vide.';
    }
    setErrors(next);
    if (Object.keys(next).length) return;

    try {
      await mutation.mutateAsync({
        presentation: form.presentation.trim(),
        similar_experience: form.similar_experience.trim(),
        methodology: form.methodology.trim(),
        estimated_budget_xaf: form.estimated_budget_xaf || null,
        proposed_duration_days: form.proposed_duration_days ? Number(form.proposed_duration_days) : null,
        team_size: form.team_size ? Number(form.team_size) : null,
        team_composition: form.team_composition.trim(),
        accepts_site_visit: form.accepts_site_visit,
      });
      setForm(EMPTY);
    } catch (error) {
      if (error instanceof ApiError) {
        const fieldErrors = Object.fromEntries(
          Object.entries(error.fields ?? {}).map(([field, messages]) => [field, messages[0]]),
        );
        setErrors(fieldErrors);
        setServerError(error.message);
      } else {
        setServerError("La candidature n'a pas pu être envoyée. Réessayez dans un instant.");
      }
    }
  };

  const closed = !data.is_open;

  return (
    <>
      <Seo
        title={data.title}
        description={`${data.description.slice(0, 155)}… Marché ${data.status_label} publié sur KEMTA — ${data.display_location}.`}
        path={`/opportunites/${data.slug}`}
        type="article"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Opportunités', path: '/opportunites' },
          { name: data.title, path: `/opportunites/${data.slug}` },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-10">
          <nav aria-label="Fil d'Ariane" className="flex flex-wrap items-center gap-1.5 text-[0.8125rem] text-k-muted">
            <Link to="/" className="hover:text-k-blue">
              Accueil
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <Link to="/opportunites" className="hover:text-k-blue">
              Opportunités
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <span className="truncate text-k-ink">{data.reference}</span>
          </nav>

          <div className="mt-6 flex flex-wrap items-center gap-2.5">
            <StatusBadge code={data.status} label={data.status_label} />
            <Badge tone="outline">{data.property_type_label}</Badge>
            {data.requires_verified_company ? (
              <Badge tone="blue">
                <BadgeCheck className="size-3.5" aria-hidden />
                Entreprises vérifiées uniquement
              </Badge>
            ) : null}
            {data.is_open && data.days_left !== null ? (
              <Badge tone={data.days_left <= 7 ? 'amber' : 'neutral'}>
                <Clock className="size-3.5" aria-hidden />
                {data.days_left <= 0 ? 'Clôture imminente' : `${data.days_left} jours restants`}
              </Badge>
            ) : null}
          </div>

          <h1 className="mt-4 max-w-[32ch]">{data.title}</h1>

          <p className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.875rem] text-k-muted">
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="size-3.5" aria-hidden />
              {data.display_location || 'Cameroun'}
            </span>
            <span>Référence {data.reference}</span>
            {data.applications_count ? <span>{data.applications_count} candidatures reçues</span> : null}
          </p>
        </div>
      </section>

      <Section className="!pt-10">
        <div className="grid gap-10 lg:grid-cols-[1.45fr_1fr] lg:gap-14">
          <div className="space-y-8">
            <div className="rounded-k-lg border border-k-line bg-white p-6">
              <h2 className="text-[1.25rem]">Le marché</h2>
              <p className="mt-3 whitespace-pre-line text-[0.9375rem] leading-relaxed text-k-muted">{data.description}</p>

              {data.specialties?.length ? (
                <div className="mt-6 border-t border-k-line pt-5">
                  <p className="text-[0.8125rem] font-medium text-k-ink">Corps d&apos;état concernés</p>
                  <ul className="mt-3 flex flex-wrap gap-2">
                    {data.specialties.map((specialty) => (
                      <li key={specialty.code}>
                        <Badge tone="outline" size="sm">
                          {specialty.name}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>

            <div>
              <SectionHeading
                eyebrow="Candidature"
                title={closed ? 'Les candidatures sont closes' : 'Déposer votre candidature'}
                description={
                  closed
                    ? 'Ce marché n\u2019accepte plus de nouvelles candidatures. Consultez les autres marchés ouverts ou inscrivez votre entreprise pour être notifiée des prochaines publications.'
                    : 'La candidature est transmise au donneur d\u2019ordre avec votre profil, vos références et votre proposition. Chaque candidat reçoit une réponse motivée.'
                }
              />

              {closed ? (
                <div className="mt-6 flex flex-wrap gap-3">
                  <ButtonLink to="/opportunites">Voir les marchés ouverts</ButtonLink>
                  <ButtonLink to="/espace-entreprise" variant="secondary">
                    Inscrire mon entreprise
                  </ButtonLink>
                </div>
              ) : !isAuthenticated ? (
                <Alert tone="info" className="mt-6" title="Connexion requise">
                  Les candidatures proviennent d&apos;entreprises identifiées : connectez-vous ou créez votre profil
                  entreprise pour candidater.
                  <div className="mt-4 flex flex-wrap gap-2.5">
                    <ButtonLink to="/connexion" size="sm">
                      Se connecter
                    </ButtonLink>
                    <ButtonLink to="/espace-entreprise" variant="secondary" size="sm">
                      Créer mon profil entreprise
                    </ButtonLink>
                  </div>
                </Alert>
              ) : data.already_applied ? (
                <Alert tone="success" className="mt-6" title="Candidature déjà envoyée">
                  Votre entreprise a déjà candidaté à ce marché. Vous serez notifié de la décision, et vous pouvez
                  suivre le dossier depuis votre espace entreprise.
                  <div className="mt-4">
                    <ButtonLink to="/espace/entreprise" size="sm">
                      Suivre ma candidature
                    </ButtonLink>
                  </div>
                </Alert>
              ) : !isCompanyUser ? (
                <Alert tone="warning" className="mt-6" title="Profil entreprise requis">
                  Votre compte est un compte client. Pour candidater à un marché, créez ou rattachez un profil
                  entreprise depuis votre espace.
                  <div className="mt-4">
                    <ButtonLink to="/espace/entreprise" size="sm">
                      Créer mon profil entreprise
                    </ButtonLink>
                  </div>
                </Alert>
              ) : (
                <form onSubmit={submit} noValidate className="mt-6 space-y-5">
                  {serverError ? <Alert tone="error">{serverError}</Alert> : null}
                  {mutation.isSuccess ? (
                    <Alert tone="success" title="Candidature transmise">
                      Votre dossier a été envoyé. Vous recevrez une notification dès que le donneur d&apos;ordre aura
                      statué.
                    </Alert>
                  ) : null}

                  <Field
                    label="Présentation de votre entreprise et motivation"
                    htmlFor="app-presentation"
                    required
                    error={errors.presentation}
                    hint="80 caractères minimum. Précisez vos références comparables et votre disponibilité."
                  >
                    <Textarea
                      id="app-presentation"
                      rows={5}
                      value={form.presentation}
                      onChange={(event) => setForm({ ...form, presentation: event.target.value })}
                      error={errors.presentation}
                      placeholder="Entreprise basée à Douala, 12 ans d'expérience, 58 chantiers livrés dont 3 immeubles R+3…"
                    />
                  </Field>

                  <Field label="Références similaires" htmlFor="app-experience" hint="Chantiers comparables, avec lieu et année">
                    <Textarea
                      id="app-experience"
                      rows={3}
                      value={form.similar_experience}
                      onChange={(event) => setForm({ ...form, similar_experience: event.target.value })}
                      placeholder="Immeuble R+3 à Bonabéri (2024), immeuble R+2 à Makepe (2022)…"
                    />
                  </Field>

                  <Field label="Méthodologie proposée" htmlFor="app-methodology" hint="Organisation du chantier, phasage, moyens">
                    <Textarea
                      id="app-methodology"
                      rows={3}
                      value={form.methodology}
                      onChange={(event) => setForm({ ...form, methodology: event.target.value })}
                      placeholder="Étude d'exécution, implantation, fondations en 6 semaines, structure coulée par niveau…"
                    />
                  </Field>

                  <div className="grid gap-5 sm:grid-cols-3">
                    <Field label="Budget proposé" htmlFor="app-budget" hint="FCFA" error={errors.estimated_budget_xaf}>
                      <Input
                        id="app-budget"
                        inputMode="numeric"
                        value={form.estimated_budget_xaf}
                        onChange={(event) =>
                          setForm({ ...form, estimated_budget_xaf: event.target.value.replace(/\D/g, '') })
                        }
                        error={errors.estimated_budget_xaf}
                        placeholder="378 000 000"
                      />
                    </Field>
                    <Field label="Délai proposé" htmlFor="app-duration" hint="Jours" error={errors.proposed_duration_days}>
                      <Input
                        id="app-duration"
                        inputMode="numeric"
                        value={form.proposed_duration_days}
                        onChange={(event) =>
                          setForm({ ...form, proposed_duration_days: event.target.value.replace(/\D/g, '') })
                        }
                        error={errors.proposed_duration_days}
                        placeholder="520"
                      />
                    </Field>
                    <Field label="Effectif mobilisé" htmlFor="app-team">
                      <Input
                        id="app-team"
                        inputMode="numeric"
                        value={form.team_size}
                        onChange={(event) => setForm({ ...form, team_size: event.target.value.replace(/\D/g, '') })}
                        placeholder="34"
                      />
                    </Field>
                  </div>

                  <Field label="Composition de l'équipe" htmlFor="app-composition">
                    <Input
                      id="app-composition"
                      value={form.team_composition}
                      onChange={(event) => setForm({ ...form, team_composition: event.target.value })}
                      placeholder="4 conducteurs, 6 chefs d'équipe, 24 ouvriers qualifiés"
                    />
                  </Field>

                  <Checkbox
                    name="app-site-visit"
                    checked={form.accepts_site_visit}
                    onChange={(checked) => setForm({ ...form, accepts_site_visit: checked })}
                    label="J'accepte une visite de site avec le donneur d'ordre avant attribution."
                  />

                  <Button
                    type="submit"
                    block
                    size="lg"
                    loading={mutation.isPending}
                    icon={<Send className="size-4" aria-hidden />}
                  >
                    Envoyer ma candidature
                  </Button>

                  <p className="text-center text-[0.75rem] text-k-muted">
                    Votre candidature et vos coordonnées ne sont transmises qu&apos;au donneur d&apos;ordre concerné.
                  </p>
                </form>
              )}
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="text-[1.0625rem]">Informations clés</h3>
              <dl className="mt-4 divide-y divide-k-line">
                {[
                  { icon: Wallet, label: 'Budget', value: data.budget_visible ? data.budget_label : 'Communiqué aux candidats' },
                  { icon: CalendarClock, label: 'Démarrage souhaité', value: data.start_date ? formatDate(data.start_date) : '—' },
                  { icon: Clock, label: 'Durée estimée', value: data.duration_days ? `${data.duration_days} jours` : '—' },
                  { icon: FileText, label: 'Dossier avant', value: data.application_deadline ? formatDate(data.application_deadline) : '—' },
                ].map((row) => {
                  const Icon = row.icon;
                  return (
                    <div key={row.label} className="flex items-start justify-between gap-4 py-3">
                      <dt className="inline-flex items-center gap-2 text-[0.8125rem] text-k-muted">
                        <Icon className="size-3.5" aria-hidden />
                        {row.label}
                      </dt>
                      <dd className="text-right text-[0.875rem] font-medium text-k-ink">{row.value}</dd>
                    </div>
                  );
                })}
              </dl>
              {!data.budget_visible && data.budget_min_xaf ? (
                <p className="mt-3 text-[0.8125rem] text-k-muted">
                  Enveloppe indicative : à partir de {formatXaf(data.budget_min_xaf, { compact: true })}
                </p>
              ) : null}
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <h3 className="flex items-center gap-2 text-[1.0625rem]">
                <ShieldCheck className="size-4 text-k-green" aria-hidden />
                Conditions de candidature
              </h3>
              <ul className="mt-4 space-y-3 text-[0.8125rem] text-k-muted">
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  {data.requires_verified_company
                    ? 'Dossier entreprise vérifié par KEMTA obligatoire.'
                    : 'Entreprise inscrite sur KEMTA (vérification recommandée).'}
                </li>
                {data.minimum_experience_years ? (
                  <li className="flex items-start gap-2">
                    <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                    {data.minimum_experience_years} ans d&apos;expérience minimum exigés.
                  </li>
                ) : null}
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Une seule candidature par entreprise et par marché.
                </li>
                <li className="flex items-start gap-2">
                  <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Décision motivée notifiée à chaque candidat.
                </li>
              </ul>
            </div>

            <div className="rounded-k-lg border border-k-line bg-k-mist p-5">
              <h3 className="flex items-center gap-2 text-[0.9375rem] font-semibold text-k-ink">
                <HelpCircle className="size-4 text-k-blue" aria-hidden />
                Besoin d&apos;aide pour candidater ?
              </h3>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">
                Un conseiller KEMTA peut relire votre dossier avant envoi.
              </p>
              <a href="tel:+237600000000" className="mt-3 inline-block text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark">
                +237 600 000 000
              </a>
            </div>
          </aside>
        </div>
      </Section>
    </>
  );
}
