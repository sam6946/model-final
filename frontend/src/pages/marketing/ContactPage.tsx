import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Mail, MapPin, MessageSquare, Phone, Send } from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Section, SectionHeading } from '@/components/layout/Section';
import { Alert } from '@/components/ui/Feedback';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Checkbox, Field, Input, Select, Textarea } from '@/components/ui/Field';
import { normalizePhone } from '@/lib/validators';
import { breadcrumbSchema } from '@/lib/seo';

type FormState = {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  topic: string;
  message: string;
  terms: boolean;
};

const TOPICS = [
  { value: 'construire', label: 'Construire un projet' },
  { value: 'suivi', label: 'Suivre un chantier en cours' },
  { value: 'entretien', label: 'Entretenir une propriété' },
  { value: 'entreprise', label: "Inscrire une entreprise BTP" },
  { value: 'partenariat', label: 'Partenariat ou presse' },
  { value: 'autre', label: 'Autre demande' },
];

const EMPTY: FormState = {
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  topic: 'construire',
  message: '',
  terms: false,
};

export default function ContactPage() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [reference, setReference] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: '' }));
  };

  const validate = () => {
    const next: Record<string, string> = {};
    if (form.first_name.trim().length < 2) next.first_name = 'Veuillez renseigner votre prénom.';
    if (form.last_name.trim().length < 2) next.last_name = 'Veuillez renseigner votre nom.';
    const phone = normalizePhone(form.phone);
    if (!phone) next.phone = 'Veuillez renseigner un numéro de téléphone valide (ex. +237 6 99 11 22 33).';
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email)) {
      next.email = "Cette adresse e-mail ne semble pas valide — elle reste facultative.";
    }
    if (form.message.trim().length < 20) {
      next.message = 'Décrivez votre besoin en quelques phrases (20 caractères minimum).';
    }
    if (!form.terms) next.terms = 'Veuillez accepter le traitement de vos données pour envoyer le message.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const data = await http.post<{ reference: string }>('/requests/', {
        kind: 'OTHER',
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: normalizePhone(form.phone),
        email: form.email.trim(),
        country: 'CM',
        description: form.message.trim(),
        payload: { canal: 'page_contact', sujet: form.topic },
        source: 'site-web/contact',
        terms_accepted: true,
      });
      setReference(data.reference);
      setForm(EMPTY);
    } catch (error) {
      setServerError(
        error instanceof Error
          ? error.message
          : "L'envoi n'a pas abouti. Vérifiez votre connexion puis réessayez.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Seo
        title="Contacter KEMTA — conseiller Douala, Yaoundé et diaspora"
        description="Parlez à un conseiller KEMTA : téléphone, WhatsApp, e-mail ou formulaire. Réponse sous 48 heures ouvrées pour votre projet de construction, de suivi de chantier ou d'entretien."
        path="/contact"
        jsonLd={breadcrumbSchema([
          { name: 'Accueil', path: '/' },
          { name: 'Contact', path: '/contact' },
        ])}
      />

      <section className="border-b border-k-line bg-white">
        <div className="k-container py-14 lg:py-16">
          <span className="k-eyebrow">
            <span className="h-px w-8 bg-k-green" aria-hidden />
            Contact
          </span>
          <h1 className="mt-5 max-w-[24ch]">Parlons de votre projet</h1>
          <p className="k-lead mt-5">
            Appelez-nous, écrivez sur WhatsApp ou laissez un message : un conseiller vous répond sous 48 heures
            ouvrées, avec une première analyse gratuite.
          </p>
        </div>
      </section>

      <Section>
        <div className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <div>
            <SectionHeading eyebrow="Nous joindre" title="Trois façons de nous parler" />

            <ul className="mt-8 space-y-4">
              <li className="rounded-k-lg border border-k-line p-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <Phone className="size-4" />
                </span>
                <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">Téléphone & WhatsApp</p>
                <div className="mt-2 space-y-1.5 text-[0.875rem]">
                  <a href="tel:+237600000000" className="block font-medium text-k-blue hover:text-k-green-dark">
                    +237 600 000 000
                  </a>
                  <a
                    href="https://wa.me/237600000000"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-k-muted hover:text-k-blue"
                  >
                    <MessageSquare className="size-3.5" aria-hidden />
                    Discuter sur WhatsApp
                  </a>
                </div>
              </li>

              <li className="rounded-k-lg border border-k-line p-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <Mail className="size-4" />
                </span>
                <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">E-mail</p>
                <div className="mt-2 space-y-1 text-[0.875rem] text-k-muted">
                  <p>
                    Projets & devis :{' '}
                    <a href="mailto:contact@kemta.cm" className="font-medium text-k-blue hover:text-k-green-dark">
                      contact@kemta.cm
                    </a>
                  </p>
                  <p>
                    Entreprises BTP :{' '}
                    <a href="mailto:entreprises@kemta.cm" className="font-medium text-k-blue hover:text-k-green-dark">
                      entreprises@kemta.cm
                    </a>
                  </p>
                  <p>
                    Sécurité & signalements :{' '}
                    <a href="mailto:securite@kemta.cm" className="font-medium text-k-blue hover:text-k-green-dark">
                      securite@kemta.cm
                    </a>
                  </p>
                </div>
              </li>

              <li className="rounded-k-lg border border-k-line p-5">
                <span className="flex size-9 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                  <MapPin className="size-4" />
                </span>
                <p className="mt-4 font-display text-[1rem] font-semibold text-k-ink">Bureaux</p>
                <p className="mt-2 text-[0.875rem] leading-relaxed text-k-muted">
                  Douala — Rue Njo-Njo, Bonanjo (siège, sur rendez-vous)
                  <br />
                  Yaoundé — Bastos, immeuble KEMTA (point d&apos;accueil, sur rendez-vous)
                </p>
                <p className="mt-3 inline-flex items-center gap-1.5 text-[0.8125rem] text-k-muted">
                  <Clock className="size-3.5 text-k-green" aria-hidden />
                  Lundi au samedi · 7 h 30 – 18 h 30
                </p>
              </li>
            </ul>
          </div>

          <div className="rounded-k-xl border border-k-line bg-k-mist p-6 sm:p-7">
            {reference ? (
              <div className="space-y-4">
                <Alert tone="success" title="Message reçu par KEMTA">
                  Votre demande porte la référence <strong>{reference}</strong>. Un conseiller vous rappelle sous 48
                  heures ouvrées. Conservez cette référence : elle permet de retrouver votre dossier à tout moment.
                </Alert>
                <div className="flex flex-col gap-2.5 sm:flex-row">
                  <ButtonLink to={`/demande/confirmation/${reference}`}>Voir la confirmation</ButtonLink>
                  <Button variant="secondary" onClick={() => setReference(null)}>
                    Envoyer un autre message
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={submit} noValidate className="space-y-5">
                <div>
                  <h2 className="text-[1.25rem]">Écrire à un conseiller</h2>
                  <p className="mt-1.5 text-[0.875rem] text-k-muted">
                    Les champs marqués d&apos;une étoile sont obligatoires. Votre numéro sert à vous rappeler.
                  </p>
                </div>

                {serverError ? <Alert tone="error">{serverError}</Alert> : null}

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Prénom" htmlFor="contact-first" required error={errors.first_name}>
                    <Input
                      id="contact-first"
                      autoComplete="given-name"
                      value={form.first_name}
                      onChange={(event) => update('first_name', event.target.value)}
                      error={errors.first_name}
                      placeholder="Aïcha"
                    />
                  </Field>
                  <Field label="Nom" htmlFor="contact-last" required error={errors.last_name}>
                    <Input
                      id="contact-last"
                      autoComplete="family-name"
                      value={form.last_name}
                      onChange={(event) => update('last_name', event.target.value)}
                      error={errors.last_name}
                      placeholder="Mbarga"
                    />
                  </Field>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Téléphone"
                    htmlFor="contact-phone"
                    required
                    error={errors.phone}
                    hint="Format accepté : +237 6 99 11 22 33 ou 6 99 11 22 33"
                  >
                    <Input
                      id="contact-phone"
                      type="tel"
                      inputMode="tel"
                      autoComplete="tel"
                      value={form.phone}
                      onChange={(event) => update('phone', event.target.value)}
                      error={errors.phone}
                      placeholder="+237 6 99 11 22 33"
                    />
                  </Field>
                  <Field label="E-mail" htmlFor="contact-email" error={errors.email}>
                    <Input
                      id="contact-email"
                      type="email"
                      autoComplete="email"
                      value={form.email}
                      onChange={(event) => update('email', event.target.value)}
                      error={errors.email}
                      placeholder="vous@exemple.cm"
                    />
                  </Field>
                </div>

                <Field label="Sujet" htmlFor="contact-topic" required>
                  <Select
                    id="contact-topic"
                    value={form.topic}
                    onChange={(event) => update('topic', event.target.value)}
                  >
                    {TOPICS.map((topic) => (
                      <option key={topic.value} value={topic.value}>
                        {topic.label}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field
                  label="Votre message"
                  htmlFor="contact-message"
                  required
                  error={errors.message}
                  hint="Précisez la ville, le type de bien et le calendrier envisagé si vous les connaissez."
                >
                  <Textarea
                    id="contact-message"
                    rows={5}
                    value={form.message}
                    onChange={(event) => update('message', event.target.value)}
                    error={errors.message}
                    placeholder="Je construis une villa à Yaoundé et je vis à Paris. Je souhaite un suivi de chantier à partir du mois prochain…"
                  />
                </Field>

                <Checkbox
                  name="contact-terms"
                  checked={form.terms}
                  onChange={(checked) => update('terms', checked)}
                  error={errors.terms}
                  label={
                    <>
                      J&apos;accepte que KEMTA traite ces informations pour me recontacter. Elles ne sont ni
                      revendues ni transmises à des tiers sans mon accord.
                    </>
                  }
                />

                <Button
                  type="submit"
                  block
                  loading={submitting}
                  icon={<Send className="size-4" aria-hidden />}
                >
                  Envoyer le message
                </Button>

                <p className="text-center text-[0.75rem] text-k-muted">
                  Besoin d&apos;un devis détaillé ?{' '}
                  <Link to="/demande" className="font-medium text-k-blue hover:text-k-green-dark">
                    Utilisez le formulaire de demande guidé
                  </Link>
                </p>
              </form>
            )}
          </div>
        </div>
      </Section>
    </>
  );
}
