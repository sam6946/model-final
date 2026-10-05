import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BadgeCheck, Lock, ShieldCheck, Smartphone, UserPlus } from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert } from '@/components/ui/Feedback';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Checkbox, Field, Input, Select } from '@/components/ui/Field';
import { ProgressSteps } from '@/components/ui/Steps';
import { useAuth } from '@/hooks/useAuth';
import { passwordStrength, normalizePhone } from '@/lib/validators';
import { formatPhone } from '@/lib/format';

const STEPS = ['Téléphone', 'Code SMS', 'Votre compte'];

const PROFILES = [
  { value: 'CUSTOMER', label: 'Je fais construire ou je possède un bien' },
  { value: 'COMPANY', label: 'Je suis une entreprise BTP' },
  { value: 'OTHER', label: 'Autre (investisseur, diaspora, institution)' },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { signIn, refreshProfile } = useAuth();

  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [ticket, setTicket] = useState<string | null>(null);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [profile, setProfile] = useState('CUSTOMER');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [city, setCity] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [terms, setTerms] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const strength = passwordStrength(password);

  const requestCode = async (event?: React.FormEvent) => {
    event?.preventDefault();
    setServerError(null);
    const normalized = normalizePhone(phone);
    if (!normalized) {
      setErrors({ phone: 'Veuillez renseigner un numéro de téléphone valide (ex. +237 6 99 11 22 33).' });
      return;
    }
    setSubmitting(true);
    try {
      const data = await http.post<{ dev_code?: string }>('/auth/otp/request/', {
        phone: normalized,
        purpose: 'REGISTER',
      });
      setDevCode(data.dev_code ?? null);
      setErrors({});
      setStep(2);
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? "Le code n'a pas pu être envoyé. Réessayez dans un instant.");
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const verifyCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    const normalized = normalizePhone(phone);
    if (!normalized) return;
    if (!/^\d{4,8}$/.test(code.trim())) {
      setErrors({ code: 'Saisissez le code à 6 chiffres reçu par SMS.' });
      return;
    }
    setSubmitting(true);
    try {
      const data = await http.post<{ verification_ticket?: string }>('/auth/otp/verify/', {
        phone: normalized,
        purpose: 'REGISTER',
        code: code.trim(),
      });
      if (!data.verification_ticket) {
        setServerError('Vérification incomplète. Demandez un nouveau code.');
        return;
      }
      setTicket(data.verification_ticket);
      setErrors({});
      setStep(3);
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? 'Le code saisi est incorrect ou a expiré.');
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const createAccount = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);

    const next: Record<string, string> = {};
    if (firstName.trim().length < 2) next.first_name = 'Veuillez renseigner votre prénom.';
    if (lastName.trim().length < 2) next.last_name = 'Veuillez renseigner votre nom.';
    if (!city.trim()) next.city = 'Indiquez votre ville de résidence.';
    if (password.length < 8) next.password = 'Choisissez un mot de passe d\'au moins 8 caractères.';
    if (password !== passwordConfirm) next.password_confirm = 'Les deux mots de passe ne correspondent pas.';
    if (!terms) next.terms_accepted = 'Vous devez accepter les conditions pour créer votre compte.';
    setErrors(next);
    if (Object.keys(next).length) return;

    const normalized = normalizePhone(phone);
    if (!normalized || !ticket) {
      setServerError('La vérification du numéro a expiré. Reprenez l\'étape précédente.');
      setStep(1);
      return;
    }

    setSubmitting(true);
    try {
      const data = await http.post<{ access: string; refresh: string }>('/auth/register/', {
        phone: normalized,
        verification_ticket: ticket,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        city: city.trim(),
        email: email.trim(),
        country: 'CM',
        role: profile === 'COMPANY' ? 'COMPANY' : 'CUSTOMER',
        terms_accepted: true,
      });
      signIn({ access: data.access, refresh: data.refresh });
      await refreshProfile();
      navigate(profile === 'COMPANY' ? '/espace/entreprise' : '/espace', { replace: true });
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? "La création du compte a échoué. Réessayez dans un instant.");
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Seo
        title="Créer un compte KEMTA"
        description="Créez votre compte KEMTA en trois minutes avec un code SMS : suivez votre chantier, vos preuves terrain et votre budget depuis votre téléphone."
        path="/inscription"
      />

      <section className="bg-k-mist">
        <div className="k-container grid gap-12 py-14 lg:grid-cols-[1fr_1fr] lg:gap-20 lg:py-20">
          <div>
            <h1 className="max-w-[22ch]">Créer mon compte KEMTA</h1>
            <p className="k-lead mt-4">
              Trois minutes, un code SMS, aucun document à scanner. Vous pourrez rattacher votre demande existante
              avec le même numéro de téléphone.
            </p>

            <ul className="mt-8 space-y-4">
              {[
                { icon: Smartphone, title: 'Téléphone comme identifiant', text: "Pas d'e-mail obligatoire : votre numéro suffit." },
                { icon: ShieldCheck, title: 'Code SMS vérifié', text: 'Votre numéro est confirmé avant la création du compte.' },
                { icon: BadgeCheck, title: 'Vos droits immédiats', text: 'Accès au suivi, preuves, rapports et factures.' },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.title} className="flex gap-4 rounded-k-lg border border-k-line bg-white p-5">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-k bg-k-blue-soft text-k-blue" aria-hidden>
                      <Icon className="size-4" />
                    </span>
                    <div>
                      <p className="font-display text-[0.9375rem] font-semibold text-k-ink">{item.title}</p>
                      <p className="mt-1 text-[0.8125rem] leading-relaxed text-k-muted">{item.text}</p>
                    </div>
                  </li>
                );
              })}
            </ul>

            <p className="mt-8 text-[0.875rem] text-k-muted">
              Déjà inscrit ?{' '}
              <Link to="/connexion" className="font-medium text-k-blue hover:text-k-green-dark">
                Connectez-vous
              </Link>
            </p>
          </div>

          <div className="rounded-k-xl border border-k-line bg-white p-6 sm:p-8">
            <ProgressSteps steps={STEPS} current={step} />

            {serverError ? (
              <Alert tone="error" className="mt-6">
                {serverError}
              </Alert>
            ) : null}

            {step === 1 ? (
              <form onSubmit={requestCode} noValidate className="mt-7 space-y-5">
                <div>
                  <h2 className="text-[1.25rem]">Votre numéro de téléphone</h2>
                  <p className="mt-1.5 text-[0.875rem] text-k-muted">
                    Nous vous envoyons un code pour confirmer que le numéro vous appartient.
                  </p>
                </div>

                <Field
                  label="Téléphone"
                  htmlFor="register-phone"
                  required
                  error={errors.phone}
                  hint="Numéro camerounais ou international (diaspora)."
                >
                  <Input
                    id="register-phone"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    value={phone}
                    onChange={(event) => {
                      setPhone(event.target.value);
                      setErrors((current) => ({ ...current, phone: '' }));
                    }}
                    error={errors.phone}
                    placeholder="+237 6 99 11 22 33"
                    autoFocus
                  />
                </Field>

                <Field label="Je suis" htmlFor="register-profile" required>
                  <Select id="register-profile" value={profile} onChange={(event) => setProfile(event.target.value)}>
                    {PROFILES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Button type="submit" block loading={submitting} icon={<Smartphone className="size-4" aria-hidden />}>
                  Recevoir mon code
                </Button>

                <p className="text-center text-[0.75rem] leading-relaxed text-k-muted">
                  En continuant, vous reconnaissez avoir lu nos conditions d&apos;utilisation et notre politique de
                  confidentialité.
                </p>
              </form>
            ) : null}

            {step === 2 ? (
              <form onSubmit={verifyCode} noValidate className="mt-7 space-y-5">
                <div>
                  <h2 className="text-[1.25rem]">Entrez le code reçu</h2>
                  <p className="mt-1.5 text-[0.875rem] text-k-muted">
                    Un SMS a été envoyé au {formatPhone(normalizePhone(phone) ?? phone) || phone}. Le code est valable
                    5 minutes.
                  </p>
                </div>

                {devCode ? (
                  <Alert tone="warning" title="Environnement de démonstration">
                    Code de test : <strong>{devCode}</strong> (affiché uniquement en développement).
                  </Alert>
                ) : null}

                <Field label="Code de vérification" htmlFor="register-code" required error={errors.code}>
                  <Input
                    id="register-code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                    error={errors.code}
                    placeholder="000000"
                    className="text-center font-display text-lg tracking-[0.4em]"
                    autoFocus
                  />
                </Field>

                <Button type="submit" block loading={submitting}>
                  Vérifier mon numéro
                </Button>

                <div className="flex items-center justify-between text-[0.8125rem]">
                  <button
                    type="button"
                    onClick={() => {
                      setStep(1);
                      setCode('');
                      setErrors({});
                    }}
                    className="inline-flex items-center gap-1.5 text-k-muted hover:text-k-blue"
                  >
                    <ArrowLeft className="size-3.5" aria-hidden />
                    Changer de numéro
                  </button>
                  <button type="button" onClick={() => void requestCode()} className="text-k-blue hover:text-k-green-dark">
                    Renvoyer le code
                  </button>
                </div>
              </form>
            ) : null}

            {step === 3 ? (
              <form onSubmit={createAccount} noValidate className="mt-7 space-y-5">
                <div>
                  <h2 className="text-[1.25rem]">Vos informations</h2>
                  <p className="mt-1.5 text-[0.875rem] text-k-muted">
                    Numéro vérifié : <strong>{formatPhone(normalizePhone(phone) ?? phone)}</strong>
                  </p>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <Field label="Prénom" htmlFor="register-first" required error={errors.first_name}>
                    <Input
                      id="register-first"
                      autoComplete="given-name"
                      value={firstName}
                      onChange={(event) => setFirstName(event.target.value)}
                      error={errors.first_name}
                      placeholder="Aïcha"
                    />
                  </Field>
                  <Field label="Nom" htmlFor="register-last" required error={errors.last_name}>
                    <Input
                      id="register-last"
                      autoComplete="family-name"
                      value={lastName}
                      onChange={(event) => setLastName(event.target.value)}
                      error={errors.last_name}
                      placeholder="Mbarga"
                    />
                  </Field>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <Field label="Ville de résidence" htmlFor="register-city" required error={errors.city}>
                    <Input
                      id="register-city"
                      autoComplete="address-level2"
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                      error={errors.city}
                      placeholder="Douala"
                    />
                  </Field>
                  <Field label="E-mail" htmlFor="register-email" error={errors.email}>
                    <Input
                      id="register-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      error={errors.email}
                      placeholder="vous@exemple.com"
                    />
                  </Field>
                </div>

                <Field
                  label="Mot de passe"
                  htmlFor="register-password"
                  required
                  error={errors.password}
                  hint="8 caractères minimum. Il sert uniquement à vous connecter sans code SMS."
                >
                  <Input
                    id="register-password"
                    type="password"
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    error={errors.password}
                    placeholder="••••••••"
                  />
                </Field>

                {password ? (
                  <div className="flex items-center gap-3">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-k-line">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          strength.score <= 2 ? 'bg-k-red' : strength.score <= 3 ? 'bg-k-amber' : 'bg-k-green'
                        }`}
                        style={{ width: `${(strength.score / 5) * 100}%` }}
                      />
                    </div>
                    <span className="text-[0.75rem] text-k-muted">{strength.label}</span>
                  </div>
                ) : null}

                <Field label="Confirmer le mot de passe" htmlFor="register-password-confirm" required error={errors.password_confirm}>
                  <Input
                    id="register-password-confirm"
                    type="password"
                    autoComplete="new-password"
                    value={passwordConfirm}
                    onChange={(event) => setPasswordConfirm(event.target.value)}
                    error={errors.password_confirm}
                    placeholder="••••••••"
                  />
                </Field>

                <Checkbox
                  name="register-terms"
                  checked={terms}
                  onChange={setTerms}
                  error={errors.terms_accepted}
                  label={
                    <>
                      J&apos;accepte les conditions d&apos;utilisation et la politique de confidentialité de KEMTA, et
                      je consens au traitement de mes données pour la gestion de mes projets.
                    </>
                  }
                />

                <Button type="submit" block loading={submitting} icon={<UserPlus className="size-4" aria-hidden />}>
                  Créer mon compte
                </Button>

                <p className="flex items-center justify-center gap-1.5 text-[0.75rem] text-k-muted">
                  <Lock className="size-3" aria-hidden />
                  Vos informations sont chiffrées et ne sont jamais revendues.
                </p>
              </form>
            ) : null}

            <div className="mt-6 border-t border-k-line pt-5">
              <ButtonLink to="/demande" variant="ghost" size="sm" block>
                Je préfère d&apos;abord déposer une demande sans compte
              </ButtonLink>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
