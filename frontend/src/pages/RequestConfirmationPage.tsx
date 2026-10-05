import { useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowRight, Bell, CalendarClock, CheckCircle2, ClipboardList, PhoneCall, Printer } from 'lucide-react';

import { Seo } from '@/components/Seo';
import { Section } from '@/components/layout/Section';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Feedback';
import { useAuth } from '@/hooks/useAuth';
import { formatPhone } from '@/lib/format';

type ConfirmationState = {
  reference?: string;
  kindLabel?: string;
  firstName?: string;
  phone?: string;
};

const NEXT_STEPS = [
  {
    icon: ClipboardList,
    title: 'Étude de votre demande',
    text: "Un chargé de suivi KEMTA analyse votre dossier, vérifie la cohérence du budget annoncé et prépare les questions utiles.",
    delay: 'Sous 24 h ouvrées',
  },
  {
    icon: PhoneCall,
    title: 'Appel de qualification',
    text: "Nous vous appelons au numéro transmis pour préciser le projet, la localisation et le calendrier. Si vous êtes à l'étranger, nous adaptons l'heure de l'appel.",
    delay: 'Sous 48 h ouvrées',
  },
  {
    icon: CalendarClock,
    title: 'Devis et calendrier',
    text: "Vous recevez un devis écrit détaillé, un calendrier prévisionnel et, si nécessaire, la liste des entreprises présélectionnées.",
    delay: '5 à 10 jours',
  },
  {
    icon: Bell,
    title: 'Ouverture de votre espace projet',
    text: "Dès validation, votre espace client affiche l'avancement, les preuves terrain, le budget et le prochain rendez-vous.",
    delay: 'À la signature',
  },
];

export default function RequestConfirmationPage() {
  const { reference } = useParams<{ reference: string }>();
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();
  const state = (location.state ?? {}) as ConfirmationState;

  const phone = state.phone ?? user?.phone ?? '';
  const firstName = state.firstName ?? user?.first_name ?? '';

  useEffect(() => {
    document.title = `Demande ${reference ?? ''} enregistrée | KEMTA`;
  }, [reference]);

  return (
    <>
      <Seo
        title="Demande enregistrée"
        description="Votre demande a bien été reçue par KEMTA. Conservez votre référence de dossier : un conseiller vous rappelle sous 48 heures ouvrées."
        path={`/demande/confirmation/${reference ?? ''}`}
        noIndex
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-14 lg:py-16">
          <span className="flex size-14 items-center justify-center rounded-full bg-k-green-pale text-k-green-dark" aria-hidden>
            <CheckCircle2 className="size-7" />
          </span>

          <h1 className="mt-6 max-w-[26ch]">
            {firstName ? `Merci ${firstName}, ` : 'Merci, '}votre demande est enregistrée
          </h1>
          <p className="k-lead mt-4">
            Votre dossier est transmis à un chargé de suivi KEMTA. Un conseiller vous rappelle sous 48 heures
            ouvrées pour qualifier votre projet et établir un devis écrit — sans engagement de votre part.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-k-lg border border-k-blue-line bg-k-blue-soft/50 px-5 py-4">
              <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Référence du dossier</p>
              <p className="mt-1 font-display text-[1.25rem] font-bold tracking-wide text-k-blue">
                {reference ?? '—'}
              </p>
              <p className="mt-1 text-[0.75rem] text-k-muted">À conserver ou à citer lors de nos échanges.</p>
            </div>

            {state.kindLabel ? (
              <div className="rounded-k-lg border border-k-line px-5 py-4">
                <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Service demandé</p>
                <p className="mt-1 font-display text-[1.0625rem] font-semibold text-k-ink">{state.kindLabel}</p>
              </div>
            ) : null}

            {phone ? (
              <div className="rounded-k-lg border border-k-line px-5 py-4">
                <p className="text-[0.75rem] uppercase tracking-wide text-k-muted">Rappel sur ce numéro</p>
                <p className="mt-1 font-display text-[1.0625rem] font-semibold text-k-ink">{formatPhone(phone)}</p>
                <Link to="/demande" className="mt-1 inline-block text-[0.75rem] text-k-blue hover:text-k-green-dark">
                  Ce numéro est erroné ? Déposer une nouvelle demande
                </Link>
              </div>
            ) : null}
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            {isAuthenticated ? (
              <ButtonLink to="/espace/demandes" iconRight={<ArrowRight className="size-4" aria-hidden />}>
                Suivre mes demandes
              </ButtonLink>
            ) : (
              <ButtonLink to="/inscription" iconRight={<ArrowRight className="size-4" aria-hidden />}>
                Créer mon compte pour tout suivre en ligne
              </ButtonLink>
            )}
            <Button
              variant="secondary"
              onClick={() => window.print()}
              icon={<Printer className="size-4" aria-hidden />}
            >
              Imprimer le récapitulatif
            </Button>
          </div>

          {!isAuthenticated ? (
            <Alert tone="info" className="mt-6 max-w-3xl" title="Pourquoi créer un compte maintenant ?">
              En créant votre compte avec ce numéro ({formatPhone(phone) || 'celui de la demande'}), votre dossier sera
              automatiquement rattaché à votre espace : vous suivrez l&apos;avancement, les preuves photo et le budget
              depuis votre téléphone.
            </Alert>
          ) : null}
        </div>
      </section>

      <Section tone="mist">
        <h2 className="text-[1.5rem]">Les prochaines étapes</h2>
        <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {NEXT_STEPS.map((item, index) => {
            const Icon = item.icon;
            return (
              <li key={item.title} className="flex flex-col rounded-k-lg border border-k-line bg-white p-5">
                <div className="flex items-center justify-between">
                  <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                    <Icon className="size-4" />
                  </span>
                  <span className="font-display text-[1.5rem] font-bold leading-none text-k-blue/12">
                    {index + 1}
                  </span>
                </div>
                <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">{item.title}</p>
                <p className="mt-2 flex-1 text-[0.8125rem] leading-relaxed text-k-muted">{item.text}</p>
                <p className="mt-4 inline-flex w-fit rounded-full bg-k-green-pale px-2.5 py-1 text-[0.6875rem] font-medium text-k-green-dark">
                  {item.delay}
                </p>
              </li>
            );
          })}
        </ol>

        <div className="mt-10 grid gap-6 rounded-k-lg border border-k-line bg-white p-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <h3 className="text-[1.125rem]">Une question urgente sur votre dossier ?</h3>
            <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
              Citez votre référence <strong>{reference}</strong> : votre interlocuteur retrouvera immédiatement votre
              dossier.
            </p>
          </div>
          <div className="flex flex-col gap-2.5 text-[0.875rem] sm:flex-row lg:justify-end">
            <a
              href="tel:+237600000000"
              className="inline-flex h-11 items-center justify-center rounded-k border border-k-line px-4 font-medium text-k-ink transition-colors hover:border-k-blue-line hover:bg-k-mist"
            >
              +237 600 000 000
            </a>
            <a
              href={`https://wa.me/237600000000?text=${encodeURIComponent(
                `Bonjour KEMTA, je vous contacte au sujet de ma demande ${reference ?? ''}.`,
              )}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-11 items-center justify-center rounded-k bg-k-green px-4 font-medium text-white transition-colors hover:bg-k-green-dark"
            >
              Écrire sur WhatsApp
            </a>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-[0.8125rem] text-k-muted">
          <Link to="/services/suivi-chantier" className="hover:text-k-blue">
            En savoir plus sur le suivi de chantier
          </Link>
          <Link to="/comment-ca-marche" className="hover:text-k-blue">
            Comment KEMTA travaille
          </Link>
          <Link to="/confiance" className="hover:text-k-blue">
            Vos données et leur sécurité
          </Link>
        </div>
      </Section>
    </>
  );
}
