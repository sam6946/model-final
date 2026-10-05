import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  Compass,
  FileText,
  Home,
  Info,
  Lock,
  PenLine,
  Ruler,
  Send,
  ShieldCheck,
} from 'lucide-react';

import { ApiError, http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section } from '@/components/layout/Section';
import { Alert, Spinner } from '@/components/ui/Feedback';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Checkbox, ChoiceGroup, Field, Input, Select, Textarea } from '@/components/ui/Field';
import { ProgressSteps } from '@/components/ui/Steps';
import { clearDraft, loadDraft, saveDraft } from '@/lib/draft';
import { normalizePhone, isValidEmail } from '@/lib/validators';
import { useLocations } from '@/lib/hooks';
import { formatDate, formatXaf } from '@/lib/format';

type KindValue = 'BUILD_PROJECT' | 'EXISTING_SITE' | 'MAINTENANCE' | 'OTHER';

type Draft = {
  kind: KindValue | null;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  city: string;
  city_of_residence: string;
  project_type: string;
  location_text: string;
  budget_min_xaf: string;
  budget_max_xaf: string;
  desired_start_date: string;
  description: string;
  has_land: boolean;
  has_plan: boolean;
  land_status: string;
  current_progress: string;
  current_company: string;
  site_manager: string;
  spent_xaf: string;
  known_issues: string;
  wants_takeover: boolean;
  property_type: string;
  maintenance_services: string[];
  maintenance_frequency: string;
  property_occupied: string;
  last_visit_date: string;
  objective: string;
  terms: boolean;
};

const DRAFT_KEY = 'demande-service';

const EMPTY_DRAFT: Draft = {
  kind: null,
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  city: '',
  city_of_residence: '',
  project_type: '',
  location_text: '',
  budget_min_xaf: '',
  budget_max_xaf: '',
  desired_start_date: '',
  description: '',
  has_land: false,
  has_plan: false,
  land_status: '',
  current_progress: '',
  current_company: '',
  site_manager: '',
  spent_xaf: '',
  known_issues: '',
  wants_takeover: false,
  property_type: '',
  maintenance_services: [],
  maintenance_frequency: '',
  property_occupied: '',
  last_visit_date: '',
  objective: '',
  terms: false,
};

const SERVICE_OPTIONS: Array<{ value: KindValue; label: string; description: string; icon: React.ReactNode }> = [
  {
    value: 'BUILD_PROJECT',
    label: 'Construire un projet',
    description: 'Villa, immeuble, local commercial : de l\'étude à la réception.',
    icon: <Building2 className="size-4" aria-hidden />,
  },
  {
    value: 'EXISTING_SITE',
    label: 'Suivre un chantier existant',
    description: 'Chantier commencé : audit, reprise en main et contrôle.',
    icon: <Ruler className="size-4" aria-hidden />,
  },
  {
    value: 'MAINTENANCE',
    label: 'Entretenir une propriété',
    description: 'Visites régulières, réparations et suivi de vos biens.',
    icon: <Home className="size-4" aria-hidden />,
  },
  {
    value: 'OTHER',
    label: 'Autre besoin',
    description: 'Audit, succession, litige, terrain, conseil.',
    icon: <Compass className="size-4" aria-hidden />,
  },
];

const PROJECT_TYPES = [
  { value: 'VILLA', label: 'Villa' },
  { value: 'MAISON', label: 'Maison simple' },
  { value: 'APPARTEMENT', label: 'Appartement' },
  { value: 'IMMEUBLE', label: 'Immeuble locatif' },
  { value: 'LOCAL_COMMERCIAL', label: 'Local commercial' },
  { value: 'AUTRE', label: 'Autre bâtiment' },
];

const LAND_STATUS = [
  { value: 'TITLED', label: 'Terrain titré (titre foncier obtenu)' },
  { value: 'BOUGHT_NOT_TITLED', label: 'Terrain acheté, titre en cours' },
  { value: 'FAMILY', label: 'Terrain familial / héritage' },
  { value: 'LOOKING', label: 'Je recherche encore un terrain' },
];

const PROGRESS_CHOICES = [
  { value: 'FONDATIONS', label: 'Fondations' },
  { value: 'ELEVATION', label: 'Élévation des murs' },
  { value: 'DALLAGE', label: 'Dallage / planchers' },
  { value: 'TOITURE', label: 'Toiture' },
  { value: 'FINITIONS', label: 'Finitions' },
  { value: 'ACHEVE', label: 'Ouvrage achevé, à contrôler' },
  { value: 'AUTRE', label: 'Autre situation' },
];

const MAINTENANCE_SERVICES = [
  { value: 'inspection', label: 'Inspection générale' },
  { value: 'plomberie', label: 'Plomberie' },
  { value: 'electricite', label: 'Électricité' },
  { value: 'peinture', label: 'Peinture' },
  { value: 'nettoyage', label: 'Nettoyage' },
  { value: 'jardinage', label: 'Jardinage / extérieurs' },
  { value: 'petites_reparations', label: 'Petites réparations' },
  { value: 'autre', label: 'Autre prestation' },
];

const FREQUENCIES = [
  { value: 'MONTHLY', label: 'Chaque mois' },
  { value: 'QUARTERLY', label: 'Chaque trimestre' },
  { value: 'SEMIANNUAL', label: 'Deux fois par an' },
  { value: 'PUNCTUAL', label: 'Une seule fois (intervention ponctuelle)' },
  { value: 'ON_DEMAND', label: 'À la demande' },
];

const OCCUPANCY = [
  { value: 'VACANT', label: 'Inoccupée' },
  { value: 'OCCUPIED_OWNER', label: 'Occupée par le propriétaire' },
  { value: 'RENTED', label: 'Louée à un locataire' },
  { value: 'FAMILY', label: 'Occupée par la famille' },
  { value: 'GUARDED', label: 'Gardien sur place' },
  { value: 'UNKNOWN', label: 'Je ne sais pas' },
];

const STEP_LABELS = ['Service', 'Votre projet', 'Vos coordonnées', 'Récapitulatif'];

const DETAIL_TITLES: Record<KindValue, string> = {
  BUILD_PROJECT: 'Décrivez le projet que vous voulez construire',
  EXISTING_SITE: 'Parlez-nous du chantier en cours',
  MAINTENANCE: 'Décrivez la propriété à entretenir',
  OTHER: 'Expliquez-nous votre besoin',
};

export default function RequestFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { data: locations } = useLocations();

  const [form, setForm] = useState<Draft>(() => {
    const stored = loadDraft<Draft>(DRAFT_KEY);
    const preset = (searchParams.get('service') ?? '') as string;
    const presetKind: KindValue | null =
      preset === 'construire'
        ? 'BUILD_PROJECT'
        : preset === 'suivi-chantier'
          ? 'EXISTING_SITE'
          : preset === 'entretien-propriete'
            ? 'MAINTENANCE'
            : preset === 'diagnostic-patrimoine'
              ? 'OTHER'
              : null;
    if (stored?.data) return { ...EMPTY_DRAFT, ...stored.data };
    return { ...EMPTY_DRAFT, kind: presetKind };
  });

  const [resumedAt] = useState<number | null>(() => loadDraft<Draft>(DRAFT_KEY)?.savedAt ?? null);
  const [step, setStep] = useState(() => (form.kind ? 1 : 1));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  /* Sauvegarde locale différée : la saisie survit à une coupure réseau. */
  useEffect(() => {
    const timer = setTimeout(() => saveDraft(DRAFT_KEY, form), 500);
    return () => clearTimeout(timer);
  }, [form]);

  const update = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => (current[key as string] ? { ...current, [key as string]: '' } : current));
  };

  const cities = useMemo(() => locations?.cities ?? [], [locations]);

  const validateStep = (target: number): boolean => {
    const next: Record<string, string> = {};

    if (target === 1) {
      if (!form.kind) next.kind = 'Veuillez choisir le service dont vous avez besoin.';
    }

    if (target === 2) {
      if (form.kind === 'BUILD_PROJECT') {
        if (!form.project_type) next.project_type = 'Veuillez indiquer le type de bâtiment à construire.';
        if (!form.location_text.trim()) next.location_text = 'Veuillez préciser la ville ou le quartier du terrain.';
        if (!form.budget_max_xaf.trim()) next.budget_max_xaf = 'Indiquez un budget estimatif, même approximatif.';
      }
      if (form.kind === 'EXISTING_SITE') {
        if (!form.location_text.trim()) next.location_text = 'Veuillez préciser la localisation du chantier.';
        if (!form.current_progress) next.current_progress = "Indiquez le niveau d'avancement actuel.";
      }
      if (form.kind === 'MAINTENANCE') {
        if (!form.property_type) next.property_type = 'Veuillez préciser le type de propriété.';
        if (!form.location_text.trim()) next.location_text = 'Veuillez préciser la localisation de la propriété.';
        if (form.maintenance_services.length === 0) {
          next.maintenance_services = 'Sélectionnez au moins une prestation souhaitée.';
        }
      }
      if (form.kind === 'OTHER' && form.description.trim().length < 20) {
        next.description = 'Décrivez votre besoin en quelques lignes (20 caractères minimum).';
      }
    }

    if (target === 3) {
      if (form.first_name.trim().length < 2) next.first_name = 'Veuillez renseigner votre prénom.';
      if (form.last_name.trim().length < 2) next.last_name = 'Veuillez renseigner votre nom.';
      if (!normalizePhone(form.phone)) {
        next.phone = 'Veuillez renseigner un numéro de téléphone valide (ex. +237 6 99 11 22 33).';
      }
      if (form.email && !isValidEmail(form.email)) {
        next.email = "Cette adresse e-mail ne semble pas valide — elle reste facultative.";
      }
      if (!form.city.trim()) next.city = 'Indiquez votre ville de résidence.';
    }

    if (target === 4) {
      if (!form.terms) next.terms = 'Veuillez accepter le traitement de vos données pour envoyer la demande.';
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const goNext = () => {
    if (!validateStep(step)) return;
    setStep((current) => Math.min(current + 1, STEP_LABELS.length));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const goBack = () => {
    setStep((current) => Math.max(current - 1, 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    if (!validateStep(4)) return;

    setSubmitting(true);
    try {
      const phone = normalizePhone(form.phone) ?? form.phone;
      const payload: Record<string, unknown> = {};
      const body: Record<string, unknown> = {
        kind: form.kind,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone,
        email: form.email.trim(),
        country: 'CM',
        city: form.city.trim(),
        city_of_residence: form.city_of_residence.trim(),
        location_text: form.location_text.trim(),
        budget_min_xaf: form.budget_min_xaf.trim(),
        budget_max_xaf: form.budget_max_xaf.trim(),
        description: form.description.trim(),
        terms_accepted: true,
        source: 'site-web/demande',
        utm: Object.fromEntries(searchParams.entries()),
      };

      if (form.kind === 'BUILD_PROJECT') {
        body.project_type = form.project_type;
        body.desired_start_date = form.desired_start_date;
        payload.has_land = form.has_land;
        payload.has_plan = form.has_plan;
        payload.land_status = form.land_status;
      }

      if (form.kind === 'EXISTING_SITE') {
        body.current_progress = form.current_progress;
        body.current_company = form.current_company.trim();
        body.site_manager = form.site_manager.trim();
        body.spent_xaf = form.spent_xaf.trim();
        body.known_issues = form.known_issues.trim();
        payload.needs_audit = true;
        payload.wants_takeover = form.wants_takeover;
      }

      if (form.kind === 'MAINTENANCE') {
        body.property_type = form.property_type;
        body.maintenance_services = form.maintenance_services;
        body.maintenance_frequency = form.maintenance_frequency;
        body.property_occupied = form.property_occupied;
        body.last_visit_date = form.last_visit_date;
        body.objective = form.objective.trim();
      }

      if (form.kind === 'OTHER') {
        body.objective = form.objective.trim();
        body.property_type = form.property_type;
      }

      body.payload = payload;

      const data = await http.post<{ reference: string; kind_label: string }>('/requests/', body);
      clearDraft(DRAFT_KEY);
      navigate(`/demande/confirmation/${data.reference}`, {
        state: {
          reference: data.reference,
          kindLabel: data.kind_label,
          firstName: form.first_name.trim(),
          phone,
        },
      });
    } catch (error) {
      if (error instanceof ApiError) {
        const fieldErrors: Record<string, string> = {};
        Object.entries(error.fields ?? {}).forEach(([field, messages]) => {
          fieldErrors[field] = messages[0];
        });
        if (Object.keys(fieldErrors).length) {
          setErrors(fieldErrors);
          setStep(2);
        }
        setServerError(error.message);
      } else {
        setServerError("L'envoi n'a pas abouti. Vos réponses sont conservées : réessayez dans un instant.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const summary = useMemo(() => {
    const rows: Array<{ label: string; value: string; step: number }> = [];
    const kindLabel = SERVICE_OPTIONS.find((option) => option.value === form.kind)?.label ?? '—';
    rows.push({ label: 'Service demandé', value: kindLabel, step: 1 });

    const firstSlot = (step: number) => {
      const existing = rows.find((row) => row.step === step);
      return !existing;
    };

    if (form.kind === 'BUILD_PROJECT') {
      rows.push({ label: 'Type de bâtiment', value: form.project_type || '—', step: 2 });
      rows.push({ label: 'Localisation', value: form.location_text || '—', step: 2 });
      if (form.budget_min_xaf) rows.push({ label: 'Budget minimum', value: formatXaf(form.budget_min_xaf), step: 2 });
      if (form.budget_max_xaf) rows.push({ label: 'Budget maximum', value: formatXaf(form.budget_max_xaf), step: 2 });
      if (firstSlot(2) && form.land_status) {
        const land = LAND_STATUS.find((item) => item.value === form.land_status)?.label ?? form.land_status;
        rows.push({ label: 'Situation du terrain', value: land, step: 2 });
      }
      if (form.desired_start_date) {
        rows.push({ label: 'Démarrage souhaité', value: formatDate(form.desired_start_date), step: 2 });
      }
    }

    if (form.kind === 'EXISTING_SITE') {
      rows.push({ label: 'Localisation du chantier', value: form.location_text || '—', step: 2 });
      const progress = PROGRESS_CHOICES.find((item) => item.value === form.current_progress)?.label ?? '—';
      rows.push({ label: 'Avancement déclaré', value: progress, step: 2 });
      if (form.current_company) rows.push({ label: 'Entreprise en place', value: form.current_company, step: 2 });
      if (form.spent_xaf) rows.push({ label: 'Déjà dépensé', value: formatXaf(form.spent_xaf), step: 2 });
    }

    if (form.kind === 'MAINTENANCE') {
      const property = PROJECT_TYPES.find((item) => item.value === form.property_type)?.label ?? form.property_type;
      rows.push({ label: 'Type de propriété', value: property || '—', step: 2 });
      rows.push({ label: 'Localisation', value: form.location_text || '—', step: 2 });
      const services = form.maintenance_services
        .map((value) => MAINTENANCE_SERVICES.find((item) => item.value === value)?.label ?? value)
        .join(', ');
      rows.push({ label: 'Prestations souhaitées', value: services || '—', step: 2 });
      const frequency = FREQUENCIES.find((item) => item.value === form.maintenance_frequency)?.label;
      if (frequency) rows.push({ label: 'Fréquence', value: frequency, step: 2 });
    }

    if (form.kind === 'OTHER' && form.description) {
      rows.push({ label: 'Votre besoin', value: form.description.slice(0, 120), step: 2 });
    }

    if (form.description && form.kind !== 'OTHER') {
      rows.push({ label: 'Précisions', value: form.description.slice(0, 120), step: 2 });
    }

    rows.push({
      label: 'Vos coordonnées',
      value: `${form.first_name} ${form.last_name} · ${form.phone}`,
      step: 3,
    });
    if (form.city) rows.push({ label: 'Ville de résidence', value: form.city, step: 3 });
    if (form.email) rows.push({ label: 'E-mail', value: form.email, step: 3 });

    return rows;
  }, [form]);

  return (
    <>
      <Seo
        title="Démarrer une demande — formulaire guidé KEMTA"
        description="Décrivez votre projet de construction, votre chantier en cours ou votre besoin d'entretien en 4 étapes. KEMTA vous rappelle sous 48 heures ouvrées."
        path="/demande"
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-10 lg:py-14">
          <nav aria-label="Fil d'Ariane" className="text-[0.8125rem] text-k-muted">
            <Link to="/" className="hover:text-k-blue">
              Accueil
            </Link>
            <span className="mx-1.5">/</span>
            <span className="text-k-ink">Demande de service</span>
          </nav>

          <h1 className="mt-6 max-w-[26ch]">Démarrer une demande</h1>
          <p className="k-lead mt-4">
            Quatre étapes, six minutes. Aucun engagement : un conseiller étudie votre dossier et vous rappelle sous
            48 heures ouvrées.
          </p>

          {resumedAt ? (
            <Alert tone="info" className="mt-6" title="Nous avons retrouvé votre saisie">
              Vous aviez commencé ce formulaire {formatDate(new Date(resumedAt).toISOString())}. Vos réponses ont été
              restaurées sur cet appareil — rien n&apos;a été envoyé à KEMTA tant que vous ne validez pas.
            </Alert>
          ) : null}
        </div>
      </section>

      <Section className="!pt-10">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_0.75fr] lg:gap-14">
          {/* ------------------------------------------------------------- formulaire */}
          <form onSubmit={submit} noValidate className="rounded-k-xl border border-k-line bg-white p-5 sm:p-7">
            <ProgressSteps steps={STEP_LABELS} current={step} />

            <div className="mt-8 space-y-7">
              {/* Étape 1 — service */}
              {step === 1 ? (
                <div>
                  <h2 className="text-[1.25rem]">De quoi avez-vous besoin ?</h2>
                  <p className="mt-2 text-[0.875rem] text-k-muted">
                    Choisissez la prestation la plus proche de votre situation. Vous pourrez préciser les détails à
                    l&apos;étape suivante.
                  </p>
                  <div className="mt-5">
                    <ChoiceGroup
                      name="service-kind"
                      options={SERVICE_OPTIONS}
                      value={form.kind}
                      onChange={(value) => update('kind', value)}
                    />
                    {errors.kind ? (
                      <p className="mt-2 text-[0.8125rem] font-medium text-k-red" role="alert">
                        {errors.kind}
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {/* Étape 2 — détails selon la branche */}
              {step === 2 && form.kind ? (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-[1.25rem]">{DETAIL_TITLES[form.kind]}</h2>
                    <p className="mt-2 text-[0.875rem] text-k-muted">
                      Plus votre description est précise, plus notre première analyse sera utile.
                    </p>
                  </div>

                  {form.kind === 'BUILD_PROJECT' ? (
                    <>
                      <div className="grid gap-5 sm:grid-cols-2">
                        <Field label="Type de bâtiment" htmlFor="project_type" required error={errors.project_type}>
                          <Select
                            id="project_type"
                            value={form.project_type}
                            onChange={(event) => update('project_type', event.target.value)}
                            error={errors.project_type}
                          >
                            <option value="">Sélectionnez…</option>
                            {PROJECT_TYPES.map((type) => (
                              <option key={type.value} value={type.value}>
                                {type.label}
                              </option>
                            ))}
                          </Select>
                        </Field>

                        <Field
                          label="Localisation du terrain"
                          htmlFor="location_text"
                          required
                          error={errors.location_text}
                          hint="Ville et quartier : « Yaoundé, Odza » ou « Douala, Bonabéri »"
                        >
                          <Input
                            id="location_text"
                            list="villes-kemta"
                            value={form.location_text}
                            onChange={(event) => update('location_text', event.target.value)}
                            error={errors.location_text}
                            placeholder="Douala, Bonapriso"
                          />
                          <datalist id="villes-kemta">
                            {cities.map((city) => (
                              <option key={city.id} value={`${city.name}, ${city.region}`} />
                            ))}
                          </datalist>
                        </Field>
                      </div>

                      <div className="grid gap-5 sm:grid-cols-3">
                        <Field label="Budget minimum" htmlFor="budget_min_xaf" hint="En francs CFA">
                          <Input
                            id="budget_min_xaf"
                            inputMode="numeric"
                            value={form.budget_min_xaf}
                            onChange={(event) => update('budget_min_xaf', event.target.value.replace(/\D/g, ''))}
                            placeholder="25 000 000"
                          />
                        </Field>
                        <Field
                          label="Budget maximum"
                          htmlFor="budget_max_xaf"
                          required
                          error={errors.budget_max_xaf}
                          hint="Estimation, même large"
                        >
                          <Input
                            id="budget_max_xaf"
                            inputMode="numeric"
                            value={form.budget_max_xaf}
                            onChange={(event) => update('budget_max_xaf', event.target.value.replace(/\D/g, ''))}
                            error={errors.budget_max_xaf}
                            placeholder="42 000 000"
                          />
                        </Field>
                        <Field label="Démarrage souhaité" htmlFor="desired_start_date">
                          <Input
                            id="desired_start_date"
                            type="date"
                            value={form.desired_start_date}
                            onChange={(event) => update('desired_start_date', event.target.value)}
                          />
                        </Field>
                      </div>

                      <Field label="Situation du terrain" htmlFor="land_status">
                        <Select
                          id="land_status"
                          value={form.land_status}
                          onChange={(event) => update('land_status', event.target.value)}
                        >
                          <option value="">Sélectionnez…</option>
                          {LAND_STATUS.map((status) => (
                            <option key={status.value} value={status.value}>
                              {status.label}
                            </option>
                          ))}
                        </Select>
                      </Field>

                      <div className="flex flex-col gap-3 rounded-k border border-k-line bg-k-mist p-4">
                        <Checkbox
                          name="has_land"
                          checked={form.has_land}
                          onChange={(checked) => update('has_land', checked)}
                          label="Je dispose déjà du terrain"
                        />
                        <Checkbox
                          name="has_plan"
                          checked={form.has_plan}
                          onChange={(checked) => update('has_plan', checked)}
                          label="J'ai déjà des plans d'architecte ou des devis d'entreprise"
                        />
                      </div>
                    </>
                  ) : null}

                  {form.kind === 'EXISTING_SITE' ? (
                    <>
                      <div className="grid gap-5 sm:grid-cols-2">
                        <Field
                          label="Localisation du chantier"
                          htmlFor="location_text"
                          required
                          error={errors.location_text}
                        >
                          <Input
                            id="location_text"
                            list="villes-kemta"
                            value={form.location_text}
                            onChange={(event) => update('location_text', event.target.value)}
                            error={errors.location_text}
                            placeholder="Yaoundé, Nsam"
                          />
                        </Field>
                        <Field label="Avancement actuel" htmlFor="current_progress" required error={errors.current_progress}>
                          <Select
                            id="current_progress"
                            value={form.current_progress}
                            onChange={(event) => update('current_progress', event.target.value)}
                            error={errors.current_progress}
                          >
                            <option value="">Sélectionnez…</option>
                            {PROGRESS_CHOICES.map((choice) => (
                              <option key={choice.value} value={choice.value}>
                                {choice.label}
                              </option>
                            ))}
                          </Select>
                        </Field>
                      </div>

                      <div className="grid gap-5 sm:grid-cols-3">
                        <Field label="Entreprise en place" htmlFor="current_company">
                          <Input
                            id="current_company"
                            value={form.current_company}
                            onChange={(event) => update('current_company', event.target.value)}
                            placeholder="Nom de l'entreprise"
                          />
                        </Field>
                        <Field label="Conducteur de travaux" htmlFor="site_manager">
                          <Input
                            id="site_manager"
                            value={form.site_manager}
                            onChange={(event) => update('site_manager', event.target.value)}
                            placeholder="Nom et téléphone"
                          />
                        </Field>
                        <Field label="Montant déjà dépensé" htmlFor="spent_xaf" hint="En francs CFA">
                          <Input
                            id="spent_xaf"
                            inputMode="numeric"
                            value={form.spent_xaf}
                            onChange={(event) => update('spent_xaf', event.target.value.replace(/\D/g, ''))}
                            placeholder="12 000 000"
                          />
                        </Field>
                      </div>

                      <Field
                        label="Problèmes constatés"
                        htmlFor="known_issues"
                        hint="Retard, arrêt de chantier, malfaçon, matériaux détournés…"
                      >
                        <Textarea
                          id="known_issues"
                          rows={3}
                          value={form.known_issues}
                          onChange={(event) => update('known_issues', event.target.value)}
                          placeholder="Le chantier est arrêté depuis deux mois, l'entreprise ne répond plus au téléphone."
                        />
                      </Field>

                      <div className="rounded-k border border-k-line bg-k-mist p-4">
                        <Checkbox
                          name="wants_takeover"
                          checked={form.wants_takeover}
                          onChange={(checked) => update('wants_takeover', checked)}
                          label="Je souhaite que KEMTA cherche une autre entreprise pour reprendre les travaux"
                        />
                      </div>
                    </>
                  ) : null}

                  {form.kind === 'MAINTENANCE' ? (
                    <>
                      <div className="grid gap-5 sm:grid-cols-2">
                        <Field label="Type de propriété" htmlFor="property_type" required error={errors.property_type}>
                          <Select
                            id="property_type"
                            value={form.property_type}
                            onChange={(event) => update('property_type', event.target.value)}
                            error={errors.property_type}
                          >
                            <option value="">Sélectionnez…</option>
                            {PROJECT_TYPES.map((type) => (
                              <option key={type.value} value={type.value}>
                                {type.label}
                              </option>
                            ))}
                          </Select>
                        </Field>
                        <Field label="Localisation" htmlFor="location_text" required error={errors.location_text}>
                          <Input
                            id="location_text"
                            list="villes-kemta"
                            value={form.location_text}
                            onChange={(event) => update('location_text', event.target.value)}
                            error={errors.location_text}
                            placeholder="Douala, Akwa"
                          />
                        </Field>
                      </div>

                      <fieldset>
                        <legend className="text-[0.8125rem] font-medium text-k-ink">
                          Prestations souhaitées<span className="ml-0.5 text-k-green"> *</span>
                        </legend>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {MAINTENANCE_SERVICES.map((service) => {
                            const selected = form.maintenance_services.includes(service.value);
                            return (
                              <label
                                key={service.value}
                                className={`cursor-pointer rounded-full border px-3.5 py-1.5 text-[0.8125rem] transition-colors ${
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
                                      'maintenance_services',
                                      event.target.checked
                                        ? [...form.maintenance_services, service.value]
                                        : form.maintenance_services.filter((item) => item !== service.value),
                                    )
                                  }
                                />
                                {service.label}
                              </label>
                            );
                          })}
                        </div>
                        {errors.maintenance_services ? (
                          <p className="mt-2 text-[0.8125rem] font-medium text-k-red" role="alert">
                            {errors.maintenance_services}
                          </p>
                        ) : null}
                      </fieldset>

                      <div className="grid gap-5 sm:grid-cols-2">
                        <Field label="Fréquence souhaitée" htmlFor="maintenance_frequency">
                          <Select
                            id="maintenance_frequency"
                            value={form.maintenance_frequency}
                            onChange={(event) => update('maintenance_frequency', event.target.value)}
                          >
                            <option value="">Sélectionnez…</option>
                            {FREQUENCIES.map((frequency) => (
                              <option key={frequency.value} value={frequency.value}>
                                {frequency.label}
                              </option>
                            ))}
                          </Select>
                        </Field>
                        <Field label="Occupation du bien" htmlFor="property_occupied">
                          <Select
                            id="property_occupied"
                            value={form.property_occupied}
                            onChange={(event) => update('property_occupied', event.target.value)}
                          >
                            <option value="">Sélectionnez…</option>
                            {OCCUPANCY.map((item) => (
                              <option key={item.value} value={item.value}>
                                {item.label}
                              </option>
                            ))}
                          </Select>
                        </Field>
                      </div>

                      <Field label="Dernière visite ou entretien" htmlFor="last_visit_date">
                        <Input
                          id="last_visit_date"
                          type="date"
                          value={form.last_visit_date}
                          onChange={(event) => update('last_visit_date', event.target.value)}
                        />
                      </Field>
                    </>
                  ) : null}

                  <Field
                    label={form.kind === 'OTHER' ? 'Votre besoin' : 'Précisions complémentaires'}
                    htmlFor="description"
                    required={form.kind === 'OTHER'}
                    error={errors.description}
                    hint={
                      form.kind === 'OTHER'
                        ? 'Décrivez la situation : audit, succession, litige, achat de terrain, conseil…'
                        : 'Nombre de pièces, contraintes du site, échéances, interlocuteurs déjà mobilisés…'
                    }
                  >
                    <Textarea
                      id="description"
                      rows={form.kind === 'OTHER' ? 6 : 4}
                      value={form.description}
                      onChange={(event) => update('description', event.target.value)}
                      error={errors.description}
                      placeholder={
                        form.kind === 'OTHER'
                          ? "Mon frère et moi héritons d'une maison à Bafoussam : nous voulons connaître son état réel et sa valeur avant de décider."
                          : "Terrain de 500 m², villa R+1 de 4 chambres avec dépendance. Démarrage souhaité en janvier, plans déjà prêts."
                      }
                    />
                  </Field>

                  {form.kind === 'MAINTENANCE' ? (
                    <Field label="Objectif de l'entretien" htmlFor="objective">
                      <Textarea
                        id="objective"
                        rows={2}
                        value={form.objective}
                        onChange={(event) => update('objective', event.target.value)}
                        placeholder="Préparer la location du bien, éviter les dégradations pendant mon absence en Europe."
                      />
                    </Field>
                  ) : null}
                </div>
              ) : null}

              {/* Étape 3 — coordonnées */}
              {step === 3 ? (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-[1.25rem]">Comment vous joindre ?</h2>
                    <p className="mt-2 text-[0.875rem] text-k-muted">
                      Le téléphone est le moyen le plus rapide : un conseiller vous rappelle. L&apos;e-mail reste
                      facultatif et n&apos;est jamais utilisé comme identifiant de connexion.
                    </p>
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Prénom" htmlFor="first_name" required error={errors.first_name}>
                      <Input
                        id="first_name"
                        autoComplete="given-name"
                        value={form.first_name}
                        onChange={(event) => update('first_name', event.target.value)}
                        error={errors.first_name}
                        placeholder="Aïcha"
                      />
                    </Field>
                    <Field label="Nom" htmlFor="last_name" required error={errors.last_name}>
                      <Input
                        id="last_name"
                        autoComplete="family-name"
                        value={form.last_name}
                        onChange={(event) => update('last_name', event.target.value)}
                        error={errors.last_name}
                        placeholder="Mbarga"
                      />
                    </Field>
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field
                      label="Téléphone / WhatsApp"
                      htmlFor="phone"
                      required
                      error={errors.phone}
                      hint="Format accepté : +237 6 99 11 22 33, ou un numéro international si vous êtes à l'étranger."
                    >
                      <Input
                        id="phone"
                        type="tel"
                        inputMode="tel"
                        autoComplete="tel"
                        value={form.phone}
                        onChange={(event) => update('phone', event.target.value)}
                        error={errors.phone}
                        placeholder="+237 6 99 11 22 33"
                      />
                    </Field>
                    <Field label="E-mail" htmlFor="email" error={errors.email}>
                      <Input
                        id="email"
                        type="email"
                        autoComplete="email"
                        value={form.email}
                        onChange={(event) => update('email', event.target.value)}
                        error={errors.email}
                        placeholder="vous@exemple.com"
                      />
                    </Field>
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Ville de résidence" htmlFor="city" required error={errors.city}>
                      <Input
                        id="city"
                        list="villes-kemta"
                        value={form.city}
                        onChange={(event) => update('city', event.target.value)}
                        error={errors.city}
                        placeholder="Douala"
                      />
                    </Field>
                    <Field label="Ville du projet (si différente)" htmlFor="city_of_residence">
                      <Input
                        id="city_of_residence"
                        value={form.city_of_residence}
                        onChange={(event) => update('city_of_residence', event.target.value)}
                        placeholder="Yaoundé"
                      />
                    </Field>
                  </div>
                </div>
              ) : null}

              {/* Étape 4 — récapitulatif */}
              {step === 4 ? (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-[1.25rem]">Vérifiez votre demande</h2>
                    <p className="mt-2 text-[0.875rem] text-k-muted">
                      Relisez les informations ci-dessous. Vous pouvez revenir en arrière pour corriger un détail
                      avant l&apos;envoi.
                    </p>
                  </div>

                  <dl className="divide-y divide-k-line rounded-k-lg border border-k-line">
                    {summary.map((row, index) => (
                      <div key={`${row.label}-${index}`} className="flex items-start justify-between gap-4 px-4 py-3.5">
                        <div className="min-w-0">
                          <dt className="text-[0.75rem] uppercase tracking-wide text-k-muted">{row.label}</dt>
                          <dd className="mt-0.5 break-words text-[0.875rem] text-k-ink">{row.value}</dd>
                        </div>
                        <button
                          type="button"
                          onClick={() => setStep(row.step)}
                          className="inline-flex shrink-0 items-center gap-1 text-[0.75rem] font-medium text-k-blue hover:text-k-green-dark"
                        >
                          <PenLine className="size-3" aria-hidden />
                          Modifier
                        </button>
                      </div>
                    ))}
                  </dl>

                  <div className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 p-4">
                    <p className="flex items-start gap-2 text-[0.8125rem] leading-relaxed text-k-ink">
                      <Info className="mt-0.5 size-4 shrink-0 text-k-blue" aria-hidden />
                      Après l&apos;envoi, vous recevrez votre référence de dossier par SMS. Un conseiller étudie votre
                      demande et vous rappelle sous 48 heures ouvrées pour qualifier le projet et établir un devis.
                    </p>
                  </div>

                  <Checkbox
                    name="terms"
                    checked={form.terms}
                    onChange={(checked) => update('terms', checked)}
                    error={errors.terms}
                    label={
                      <>
                        J&apos;accepte que KEMTA traite mes informations pour étudier ma demande et me recontacter.
                        Elles ne sont ni revendues ni transmises à des tiers sans mon accord, et je peux demander
                        leur suppression à tout moment.
                      </>
                    }
                  />

                  {serverError ? <Alert tone="error">{serverError}</Alert> : null}
                </div>
              ) : null}
            </div>

            {/* Navigation */}
            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-k-line pt-6 sm:flex-row sm:items-center sm:justify-between">
              {step > 1 ? (
                <Button type="button" variant="ghost" onClick={goBack} icon={<ArrowLeft className="size-4" aria-hidden />}>
                  Étape précédente
                </Button>
              ) : (
                <Link to="/" className="text-[0.875rem] text-k-muted hover:text-k-blue">
                  Annuler et revenir à l&apos;accueil
                </Link>
              )}

              {step < 4 ? (
                <Button type="button" onClick={goNext} iconRight={<ArrowRight className="size-4" aria-hidden />}>
                  Continuer
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="lg"
                  loading={submitting}
                  icon={submitting ? undefined : <Send className="size-4" aria-hidden />}
                >
                  Envoyer ma demande
                </Button>
              )}
            </div>
          </form>

          {/* --------------------------------------------------------- colonne latérale */}
          <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
            <div className="rounded-k-lg border border-k-line bg-k-mist p-5">
              <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
                <ShieldCheck className="size-4 text-k-green" aria-hidden />
                Vos données restent les vôtres
              </p>
              <ul className="mt-3 space-y-2.5 text-[0.8125rem] leading-relaxed text-k-muted">
                <li className="flex gap-2">
                  <Check className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Votre saisie est conservée sur votre appareil tant que vous n&apos;envoyez pas le formulaire.
                </li>
                <li className="flex gap-2">
                  <Check className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Aucun numéro n&apos;est partagé avec une entreprise BTP sans votre accord écrit.
                </li>
                <li className="flex gap-2">
                  <Check className="mt-0.5 size-3.5 shrink-0 text-k-green" aria-hidden />
                  Vous pouvez demander la suppression de votre dossier à tout moment.
                </li>
              </ul>
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
                <FileText className="size-4 text-k-blue" aria-hidden />
                Ce qui se passe ensuite
              </p>
              <ol className="mt-3 space-y-3 text-[0.8125rem] leading-relaxed text-k-muted">
                <li className="flex gap-2.5">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-k-blue-soft text-[0.6875rem] font-semibold text-k-blue" aria-hidden>
                    1
                  </span>
                  Vous recevez votre référence de dossier par SMS.
                </li>
                <li className="flex gap-2.5">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-k-blue-soft text-[0.6875rem] font-semibold text-k-blue" aria-hidden>
                    2
                  </span>
                  Un conseiller vous appelle sous 48 h ouvrées pour qualifier le besoin.
                </li>
                <li className="flex gap-2.5">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-k-blue-soft text-[0.6875rem] font-semibold text-k-blue" aria-hidden>
                    3
                  </span>
                  Vous recevez un devis écrit et un calendrier, sans engagement.
                </li>
              </ol>
            </div>

            <div className="rounded-k-lg border border-k-line bg-white p-5">
              <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
                <Lock className="size-4 text-k-blue" aria-hidden />
                Besoin d&apos;aide pour remplir ?
              </p>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">
                Un conseiller peut remplir la demande avec vous par téléphone.
              </p>
              <a
                href="tel:+237600000000"
                className="mt-3 inline-flex text-[0.875rem] font-medium text-k-blue hover:text-k-green-dark"
              >
                +237 600 000 000
              </a>
              <div className="mt-4 border-t border-k-line pt-4">
                {submitting ? <Spinner label="Envoi de votre demande…" /> : null}
                <p className="text-[0.75rem] text-k-muted">
                  Lundi au samedi · 7 h 30 – 18 h 30 (heure du Cameroun)
                </p>
              </div>
            </div>

            <div className="rounded-k-lg border border-k-line bg-k-mist p-5">
              <p className="flex items-center gap-2 font-display text-[0.9375rem] font-semibold text-k-ink">
                <CheckCircle2 className="size-4 text-k-green" aria-hidden />
                Déjà client ?
              </p>
              <p className="mt-2 text-[0.8125rem] leading-relaxed text-k-muted">
                Suivez vos projets, vos preuves et vos factures depuis votre espace.
              </p>
              <ButtonLink to="/connexion" variant="secondary" size="sm" className="mt-3">
                Me connecter
              </ButtonLink>
            </div>
          </aside>
        </div>
      </Section>
    </>
  );
}
