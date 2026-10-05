import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BadgeCheck, Building2, CheckCircle2, FileUp, ShieldCheck, Wrench } from 'lucide-react';

import { ApiError, http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Alert } from '@/components/ui/Feedback';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Checkbox, Field, Input, Select, Textarea } from '@/components/ui/Field';
import { ProgressSteps } from '@/components/ui/Steps';
import { COMPANY_STEPS } from '@/lib/content';
import { useAuth } from '@/hooks/useAuth';
import { useSpecialties } from '@/lib/hooks';
import { breadcrumbSchema } from '@/lib/seo';
import { normalizePhone } from '@/lib/validators';

const STEPS = ['Identité', 'Activité', 'Métiers & zones', 'Dossier'];

const REGIONS = [
  { value: 'LT', label: 'Littoral' },
  { value: 'CE', label: 'Centre' },
  { value: 'OU', label: 'Ouest' },
  { value: 'NW', label: 'Nord-Ouest' },
  { value: 'SW', label: 'Sud-Ouest' },
  { value: 'SU', label: 'Sud' },
  { value: 'NO', label: 'Nord' },
  { value: 'AD', label: 'Adamaoua' },
  { value: 'ES', label: 'Est' },
  { value: 'EN', label: 'Extrême-Nord' },
];

const DOCUMENT_KINDS = [
  { value: 'REGISTRE_COMMERCE', label: 'Registre de commerce et du crédit mobilier (RCCM)' },
  { value: 'ATTESTATION_FISCALE', label: 'Attestation de non-redevance fiscale' },
  { value: 'CNPS', label: 'Attestation CNPS' },
  { value: 'ASSURANCE', label: 'Attestation d\u2019assurance responsabilité civile' },
];

export default function CompanyOnboardingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const { data: specialties } = useSpecialties();

  const [step, setStep] = useState(1);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<{ slug: string; name: string } | null>(null);

  const [form, setForm] = useState({
    name: '',
    legal_name: '',
    registration_number: '',
    tax_number: '',
    city: '',
    region: 'LT',
    address: '',
    phone: user?.phone ?? '',
    email: '',
    description: '',
    years_experience: '',
    employees_count: '',
    projects_count: '',
    equipment_summary: '',
    specialties: [] as number[],
    intervention_regions: [] as string[],
    terms: false,
  });

  const specialtyOptions = useMemo(() => specialties?.results ?? [], [specialties]);

  const update = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => (current[key as string] ? { ...current, [key as string]: '' } : current));
  };

  const validate = (target: number) => {
    const next: Record<string, string> = {};
    if (target === 1) {
      if (form.name.trim().length < 3) next.name = "Indiquez la raison commerciale de l'entreprise.";
      if (!form.registration_number.trim()) next.registration_number = 'Le numéro RCCM est obligatoire pour la vérification.';
      if (!form.city.trim()) next.city = 'Indiquez la ville du siège.';
      if (!normalizePhone(form.phone)) next.phone = 'Indiquez un numéro de téléphone joignable.';
    }
    if (target === 2) {
      if (form.description.trim().length < 80) {
        next.description = "Présentez votre entreprise en 80 caractères minimum (activités, références, moyens).";
      }
      if (!form.years_experience) next.years_experience = "Indiquez vos années d'expérience.";
      if (!form.employees_count) next.employees_count = 'Indiquez votre effectif.';
    }
    if (target === 3) {
      if (form.specialties.length === 0) next.specialties = 'Sélectionnez au moins un corps d\u2019état.';
      if (form.intervention_regions.length === 0) next.intervention_regions = 'Indiquez au moins une région d\u2019intervention.';
    }
    if (target === 4 && !form.terms) {
      next.terms = 'Vous devez certifier l\u2019exactitude des informations fournies.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const next = () => {
    if (!validate(step)) return;
    setStep((current) => Math.min(current + 1, STEPS.length));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const back = () => {
    setStep((current) => Math.max(1, current - 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    if (!validate(4)) return;

    setSubmitting(true);
    try {
      const data = await http.post<{ company: { slug: string; name: string } }>('/company/mine/', {
        name: form.name.trim(),
        legal_name: form.legal_name.trim(),
        registration_number: form.registration_number.trim(),
        tax_number: form.tax_number.trim(),
        city: form.city.trim(),
        region: form.region,
        address: form.address.trim(),
        phone: normalizePhone(form.phone) ?? form.phone,
        email: form.email.trim(),
        description: form.description.trim(),
        years_experience: Number(form.years_experience) || 0,
        employees_count: Number(form.employees_count) || 1,
        projects_count: Number(form.projects_count) || 0,
        equipment_summary: form.equipment_summary.trim(),
        specialties: form.specialties,
        intervention_regions: form.intervention_regions,
      });
      setCreated({ slug: data.company.slug, name: data.company.name });
    } catch (error) {
      if (error instanceof ApiError) {
        setServerError(error.message);
        const fieldErrors = Object.fromEntries(
          Object.entries(error.fields ?? {}).map(([field, messages]) => [field, messages[0]]),
        );
        setErrors(fieldErrors);
        if (error.code === 'company_exists') {
          navigate('/espace/entreprise');
        }
      } else {
        setServerError("La création du profil a échoué. Réessayez dans un instant.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Seo
        title="Inscrire mon entreprise BTP sur KEMTA"
        description="Créez votre profil entreprise, faites vérifier votre dossier administratif et recevez des marchés : RCCM, attestation fiscale, CNPS et références contrôlés par KEMTA."
        path="/espace-entreprise"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Entreprises BTP', path: '/entreprises-btp' },
          { name: 'Inscrire mon entreprise', path: '/espace-entreprise' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-12 lg:py-16">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Espace entreprise BTP
          </span>
          <h1 className="mt-5 max-w-[28ch]">Faites vérifier votre entreprise et accédez aux marchés</h1>
          <p className="k-lead mt-5">
            L&apos;inscription est gratuite. Une fois votre dossier contrôlé par KEMTA, votre profil devient visible
            par les clients et vous pouvez candidater aux marchés publiés sur la plateforme.
          </p>

          <ol className="mt-9 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
            {COMPANY_STEPS.map((item, index) => (
              <li key={item.title} className="border-t border-k-line pt-4">
                <span className="font-display text-[0.8125rem] font-semibold text-k-blue/70">
                  Étape {index + 1}
                </span>
                <p className="mt-1.5 font-display text-[0.9375rem] font-semibold text-k-ink">{item.title}</p>
                <p className="mt-1 text-[0.8125rem] leading-relaxed text-k-muted">{item.description}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <Section>
        {created ? (
          <div className="mx-auto max-w-2xl rounded-k-xl border border-k-green/25 bg-k-green-pale/60 p-8 text-center">
            <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-white text-k-green-dark" aria-hidden>
              <CheckCircle2 className="size-7" />
            </span>
            <h2 className="mt-5 text-[1.5rem]">Profil créé : {created.name}</h2>
            <p className="mt-3 text-[0.9375rem] leading-relaxed text-k-muted">
              Votre entreprise est enregistrée. Déposez maintenant vos pièces administratives depuis votre espace
              entreprise : notre équipe les contrôle sous 5 jours ouvrés, puis votre badge « Vérifiée » est activé.
            </p>
            <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
              <ButtonLink to="/espace/entreprise">Déposer mes pièces</ButtonLink>
              <ButtonLink to={`/entreprises/${created.slug}`} variant="secondary">
                Voir mon profil public
              </ButtonLink>
            </div>
          </div>
        ) : (
          <div className="grid gap-12 lg:grid-cols-[1.4fr_0.85fr] lg:gap-16">
            <form onSubmit={submit} noValidate className="rounded-k-xl border border-k-line bg-white p-5 sm:p-7">
              <ProgressSteps steps={STEPS} current={step} />

              {serverError ? (
                <Alert tone="error" className="mt-6">
                  {serverError}
                </Alert>
              ) : null}

              <div className="mt-8 space-y-6">
                {step === 1 ? (
                  <>
                    <h2 className="text-[1.25rem]">Identité légale de l&apos;entreprise</h2>
                    <div className="grid gap-5 sm:grid-cols-2">
                      <Field label="Raison commerciale" htmlFor="c-name" required error={errors.name}>
                        <Input
                          id="c-name"
                          value={form.name}
                          onChange={(event) => update('name', event.target.value)}
                          error={errors.name}
                          placeholder="BTP Sawa Construction SARL"
                        />
                      </Field>
                      <Field label="Dénomination légale" htmlFor="c-legal">
                        <Input
                          id="c-legal"
                          value={form.legal_name}
                          onChange={(event) => update('legal_name', event.target.value)}
                          placeholder="BTP SAWA CONSTRUCTION SARL"
                        />
                      </Field>
                      <Field
                        label="Numéro RCCM"
                        htmlFor="c-rccm"
                        required
                        error={errors.registration_number}
                        hint="Registre de commerce et du crédit mobilier"
                      >
                        <Input
                          id="c-rccm"
                          value={form.registration_number}
                          onChange={(event) => update('registration_number', event.target.value)}
                          error={errors.registration_number}
                          placeholder="RC/DLA/2012/B/1234"
                        />
                      </Field>
                      <Field label="Numéro contribuable" htmlFor="c-tax">
                        <Input
                          id="c-tax"
                          value={form.tax_number}
                          onChange={(event) => update('tax_number', event.target.value)}
                          placeholder="M021234567890A"
                        />
                      </Field>
                      <Field label="Ville du siège" htmlFor="c-city" required error={errors.city}>
                        <Input
                          id="c-city"
                          value={form.city}
                          onChange={(event) => update('city', event.target.value)}
                          error={errors.city}
                          placeholder="Douala"
                        />
                      </Field>
                      <Field label="Région" htmlFor="c-region" required>
                        <Select id="c-region" value={form.region} onChange={(event) => update('region', event.target.value)}>
                          {REGIONS.map((region) => (
                            <option key={region.value} value={region.value}>
                              {region.label}
                            </option>
                          ))}
                        </Select>
                      </Field>
                      <Field label="Adresse du siège" htmlFor="c-address">
                        <Input
                          id="c-address"
                          value={form.address}
                          onChange={(event) => update('address', event.target.value)}
                          placeholder="Rue Njo-Njo, Bonanjo"
                        />
                      </Field>
                      <Field label="Téléphone professionnel" htmlFor="c-phone" required error={errors.phone}>
                        <Input
                          id="c-phone"
                          type="tel"
                          value={form.phone}
                          onChange={(event) => update('phone', event.target.value)}
                          error={errors.phone}
                          placeholder="+237 6 99 11 22 33"
                        />
                      </Field>
                      <Field label="E-mail professionnel" htmlFor="c-email">
                        <Input
                          id="c-email"
                          type="email"
                          value={form.email}
                          onChange={(event) => update('email', event.target.value)}
                          placeholder="contact@entreprise.cm"
                        />
                      </Field>
                    </div>
                  </>
                ) : null}

                {step === 2 ? (
                  <>
                    <h2 className="text-[1.25rem]">Votre activité</h2>
                    <Field
                      label="Présentation de l'entreprise"
                      htmlFor="c-description"
                      required
                      error={errors.description}
                      hint="80 caractères minimum : spécialités, types de chantiers, références marquantes."
                    >
                      <Textarea
                        id="c-description"
                        rows={5}
                        value={form.description}
                        onChange={(event) => update('description', event.target.value)}
                        error={errors.description}
                        placeholder="Entreprise générale de bâtiment basée à Douala depuis 2012 : gros œuvre, second œuvre et finitions pour villas, immeubles et locaux professionnels."
                      />
                    </Field>

                    <div className="grid gap-5 sm:grid-cols-3">
                      <Field label="Années d'expérience" htmlFor="c-years" required error={errors.years_experience}>
                        <Input
                          id="c-years"
                          inputMode="numeric"
                          value={form.years_experience}
                          onChange={(event) => update('years_experience', event.target.value.replace(/\D/g, ''))}
                          error={errors.years_experience}
                          placeholder="12"
                        />
                      </Field>
                      <Field label="Effectif" htmlFor="c-employees" required error={errors.employees_count}>
                        <Input
                          id="c-employees"
                          inputMode="numeric"
                          value={form.employees_count}
                          onChange={(event) => update('employees_count', event.target.value.replace(/\D/g, ''))}
                          error={errors.employees_count}
                          placeholder="34"
                        />
                      </Field>
                      <Field label="Chantiers réalisés" htmlFor="c-projects">
                        <Input
                          id="c-projects"
                          inputMode="numeric"
                          value={form.projects_count}
                          onChange={(event) => update('projects_count', event.target.value.replace(/\D/g, ''))}
                          placeholder="58"
                        />
                      </Field>
                    </div>

                    <Field label="Matériel et moyens" htmlFor="c-equipment" hint="Utile pour rassurer les clients sur votre capacité">
                      <Textarea
                        id="c-equipment"
                        rows={3}
                        value={form.equipment_summary}
                        onChange={(event) => update('equipment_summary', event.target.value)}
                        placeholder="Bétonnières, échafaudages, camion benne, outillage électroportatif, 2 pick-up de chantier."
                      />
                    </Field>
                  </>
                ) : null}

                {step === 3 ? (
                  <>
                    <h2 className="text-[1.25rem]">Métiers et zones d&apos;intervention</h2>

                    <fieldset>
                      <legend className="text-[0.8125rem] font-medium text-k-ink">
                        Corps d&apos;état maîtrisés<span className="ml-0.5 text-k-green"> *</span>
                      </legend>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {specialtyOptions.map((specialty) => {
                          const selected = form.specialties.includes(specialty.id);
                          return (
                            <label
                              key={specialty.id}
                              className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-[0.8125rem] transition-colors ${
                                selected
                                  ? 'border-k-green bg-k-green-pale text-k-green-dark'
                                  : 'border-k-line bg-white text-k-ink hover:border-k-blue-line'
                              }`}
                            >
                              <input
                                type="checkbox"
                                className="sr-only"
                                checked={selected}
                                onChange={(event) =>
                                  update(
                                    'specialties',
                                    event.target.checked
                                      ? [...form.specialties, specialty.id]
                                      : form.specialties.filter((id) => id !== specialty.id),
                                  )
                                }
                              />
                              {selected ? <BadgeCheck className="size-3.5" aria-hidden /> : <Wrench className="size-3.5" aria-hidden />}
                              {specialty.name}
                            </label>
                          );
                        })}
                      </div>
                      {errors.specialties ? (
                        <p className="mt-2 text-[0.8125rem] font-medium text-k-red" role="alert">
                          {errors.specialties}
                        </p>
                      ) : null}
                    </fieldset>

                    <fieldset>
                      <legend className="text-[0.8125rem] font-medium text-k-ink">
                        Régions d&apos;intervention<span className="ml-0.5 text-k-green"> *</span>
                      </legend>
                      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                        {REGIONS.map((region) => {
                          const selected = form.intervention_regions.includes(region.value);
                          return (
                            <Checkbox
                              key={region.value}
                              name={`region-${region.value}`}
                              checked={selected}
                              onChange={(checked) =>
                                update(
                                  'intervention_regions',
                                  checked
                                    ? [...form.intervention_regions, region.value]
                                    : form.intervention_regions.filter((value) => value !== region.value),
                                )
                              }
                              label={region.label}
                            />
                          );
                        })}
                      </div>
                      {errors.intervention_regions ? (
                        <p className="mt-2 text-[0.8125rem] font-medium text-k-red" role="alert">
                          {errors.intervention_regions}
                        </p>
                      ) : null}
                    </fieldset>
                  </>
                ) : null}

                {step === 4 ? (
                  <>
                    <h2 className="text-[1.25rem]">Vérification et engagement</h2>
                    <p className="text-[0.875rem] leading-relaxed text-k-muted">
                      Après création du profil, vous déposerez vos pièces justificatives depuis votre espace
                      entreprise. Voici celles qui seront demandées :
                    </p>

                    <ul className="space-y-2.5">
                      {DOCUMENT_KINDS.map((kind) => (
                        <li key={kind.value} className="flex items-start gap-2.5 text-[0.875rem] text-k-ink/85">
                          <FileUp className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
                          {kind.label}
                        </li>
                      ))}
                    </ul>

                    <Alert tone="info" title="Ce qui est attendu de vous">
                      Des documents lisibles, à jour, au nom de l&apos;entreprise. Un dossier incomplet est renvoyé
                      avec la liste précise des pièces manquantes — jamais refusé sans explication.
                    </Alert>

                    <Checkbox
                      name="company-terms"
                      checked={form.terms}
                      onChange={(checked) => update('terms', checked)}
                      error={errors.terms}
                      label="Je certifie l'exactitude des informations fournies et j'autorise KEMTA à vérifier mes pièces administratives auprès des organismes concernés."
                    />
                  </>
                ) : null}
              </div>

              <div className="mt-8 flex flex-col-reverse gap-3 border-t border-k-line pt-6 sm:flex-row sm:items-center sm:justify-between">
                {step > 1 ? (
                  <Button type="button" variant="ghost" onClick={back} icon={<ArrowLeft className="size-4" aria-hidden />}>
                    Étape précédente
                  </Button>
                ) : (
                  <span className="text-[0.8125rem] text-k-muted">Étape 1 sur 4 · environ 5 minutes</span>
                )}

                {step < 4 ? (
                  <Button type="button" onClick={next} iconRight={<ArrowRight className="size-4" aria-hidden />}>
                    Continuer
                  </Button>
                ) : (
                  <Button type="submit" size="lg" loading={submitting} icon={<Building2 className="size-4" aria-hidden />}>
                    Créer mon profil entreprise
                  </Button>
                )}
              </div>
            </form>

            <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
              <div className="rounded-k-lg border border-k-line bg-k-mist p-5">
                <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
                  <ShieldCheck className="size-4 text-k-green" aria-hidden />
                  Pourquoi la vérification ?
                </p>
                <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">
                  Le badge « Vérifiée » est le premier critère de choix des clients sur KEMTA. Il garantit que
                  l&apos;entreprise existe légalement, paie ses impôts et ses cotisations sociales, et que ses
                  références de chantier ont été contrôlées.
                </p>
              </div>

              <div className="rounded-k-lg border border-k-line bg-white p-5">
                <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Ce que vous obtenez</p>
                <ul className="mt-3 space-y-2.5 text-[0.8125rem] text-k-muted">
                  {[
                    'Un profil public indexable, avec vos réalisations.',
                    'L\u2019accès aux marchés réservés aux entreprises vérifiées.',
                    'Des demandes de devis qualifiées par KEMTA.',
                    'Une réputation mesurée par des avis clients vérifiés.',
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <BadgeCheck className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {!isAuthenticated ? (
                <Alert tone="warning" title="Connexion requise">
                  Pour créer un profil entreprise, connectez-vous d&apos;abord avec votre numéro de téléphone.
                  <div className="mt-4 flex flex-wrap gap-2.5">
                    <ButtonLink to="/inscription" size="sm">
                      Créer un compte
                    </ButtonLink>
                    <ButtonLink to="/connexion" variant="secondary" size="sm">
                      Se connecter
                    </ButtonLink>
                  </div>
                </Alert>
              ) : null}
            </aside>
          </div>
        )}
      </Section>

      <Section tone="mist" className="!py-14">
        <SectionHeading
          eyebrow="Questions fréquentes"
          title="Ce que demandent les entreprises avant de s'inscrire"
        />
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[
            {
              question: "L'inscription est-elle payante ?",
              answer:
                "Non. La création du profil et la vérification sont gratuites. Des offres payantes existent pour la visibilité et un nombre élargi de candidatures.",
            },
            {
              question: 'Combien de temps pour être vérifiée ?',
              answer:
                'Cinq jours ouvrés en moyenne après dépôt de toutes les pièces. Vous êtes notifié à chaque étape, y compris en cas de pièce manquante.',
            },
            {
              question: 'KEMTA prend-il une commission sur nos chantiers ?',
              answer:
                'Non. KEMTA est rémunéré par le client pour la prestation de suivi. Aucune rétrocommission n’est prélevée sur les entreprises du réseau.',
            },
            {
              question: 'Puis-je candidater sans être vérifiée ?',
              answer:
                'Sur les marchés marqués « entreprises vérifiées », non. Sur les autres marchés, votre candidature est acceptée mais la vérification reste un avantage décisif.',
            },
            {
              question: 'Mes documents sont-ils publics ?',
              answer:
                'Jamais. Vos pièces sont visibles uniquement par l’équipe KEMTA chargée de la vérification. Le public voit le badge et la date de vérification.',
            },
            {
              question: 'Comment sont gérés les avis ?',
              answer:
                'Seuls les clients dont le projet est suivi par KEMTA peuvent noter une entreprise, sur la qualité, le respect des délais et la communication.',
            },
          ].map((item) => (
            <div key={item.question} className="rounded-k-lg border border-k-line bg-white p-5">
              <p className="font-display text-[0.9375rem] font-semibold text-k-ink">{item.question}</p>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">{item.answer}</p>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
