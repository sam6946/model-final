import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, Lock, ShieldCheck, Smartphone } from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert } from '@/components/ui/Feedback';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Field';
import { useAuth } from '@/hooks/useAuth';
import { normalizePhone } from '@/lib/validators';
import { formatPhone } from '@/lib/format';

type Mode = 'password' | 'otp';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, refreshProfile } = useAuth();
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/espace';

  const [mode, setMode] = useState<Mode>('password');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [resendIn, setResendIn] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validatePhone = () => {
    const normalized = normalizePhone(phone);
    if (!normalized) {
      setErrors({ phone: 'Veuillez renseigner votre numéro de téléphone (ex. +237 6 99 11 22 33).' });
      return null;
    }
    return normalized;
  };

  const submitPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    const normalized = validatePhone();
    if (!normalized) return;
    if (!password) {
      setErrors({ password: 'Veuillez renseigner votre mot de passe.' });
      return;
    }

    setSubmitting(true);
    try {
      const data = await http.post<{ access: string; refresh: string }>('/auth/login/', {
        phone: normalized,
        password,
      });
      signIn({ access: data.access, refresh: data.refresh });
      await refreshProfile();
      navigate(redirectTo, { replace: true });
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? 'La connexion a échoué. Vérifiez vos identifiants puis réessayez.');
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const requestCode = async () => {
    setServerError(null);
    const normalized = validatePhone();
    if (!normalized) return;
    setSubmitting(true);
    try {
      const data = await http.post<{ dev_code?: string; resend_in?: number; phone_display?: string }>(
        '/auth/login/otp/request/',
        { phone: normalized, purpose: 'LOGIN' },
      );
      setCodeSent(true);
      setDevCode(data.dev_code ?? null);
      setResendIn(data.resend_in ?? 45);
      setErrors({});
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? "Le code n'a pas pu être envoyé. Vérifiez le numéro puis réessayez.");
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const submitCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);
    const normalized = validatePhone();
    if (!normalized) return;
    if (!/^\d{4,8}$/.test(code.trim())) {
      setErrors({ code: 'Saisissez le code à 6 chiffres reçu par SMS.' });
      return;
    }

    setSubmitting(true);
    try {
      const data = await http.post<{ access?: string; refresh?: string }>('/auth/login/otp/verify/', {
        phone: normalized,
        purpose: 'LOGIN',
        code: code.trim(),
      });
      if (!data.access || !data.refresh) {
        setServerError("Connexion incomplète. Demandez un nouveau code puis réessayez.");
        return;
      }
      signIn({ access: data.access, refresh: data.refresh });
      await refreshProfile();
      navigate(redirectTo, { replace: true });
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

  return (
    <>
      <Seo
        title="Connexion à votre espace KEMTA"
        description="Connectez-vous à votre espace KEMTA par mot de passe ou par code SMS pour suivre vos projets, vos preuves terrain et vos factures."
        path="/connexion"
      />

      <section className="bg-k-mist">
        <div className="k-container grid gap-12 py-14 lg:grid-cols-[1fr_1fr] lg:gap-20 lg:py-20">
          <div>
            <h1 className="max-w-[20ch]">Accéder à mon espace</h1>
            <p className="k-lead mt-4">
              Suivez l&apos;avancement de votre chantier, consultez les preuves photo, vérifiez votre budget et
              retrouvez vos factures.
            </p>

            <ul className="mt-8 space-y-3 text-[0.875rem] text-k-muted">
              <li className="flex items-start gap-2.5">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                Connexion sécurisée : mot de passe ou code SMS à usage unique.
              </li>
              <li className="flex items-start gap-2.5">
                <Lock className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                Vos données de chantier restent privées, visibles par vous et l&apos;équipe KEMTA uniquement.
              </li>
              <li className="flex items-start gap-2.5">
                <Smartphone className="mt-0.5 size-4 shrink-0 text-k-green" aria-hidden />
                Le téléphone est votre identifiant : aucun e-mail n&apos;est exigé.
              </li>
            </ul>

            <div className="mt-10 rounded-k-lg border border-k-line bg-white p-5">
              <p className="font-display text-[0.9375rem] font-semibold text-k-ink">Pas encore de compte ?</p>
              <p className="mt-1.5 text-[0.875rem] text-k-muted">
                L&apos;inscription se fait en trois minutes avec un code SMS.
              </p>
              <ButtonLink to="/inscription" variant="secondary" size="sm" className="mt-4">
                Créer mon compte
              </ButtonLink>
            </div>
          </div>

          <div className="rounded-k-xl border border-k-line bg-white p-6 sm:p-8">
            <div className="flex gap-2 rounded-k bg-k-mist p-1" role="tablist">
              {(
                [
                  { value: 'password', label: 'Mot de passe', icon: KeyRound },
                  { value: 'otp', label: 'Code SMS', icon: Smartphone },
                ] as const
              ).map((tab) => {
                const Icon = tab.icon;
                const active = mode === tab.value;
                return (
                  <button
                    key={tab.value}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => {
                      setMode(tab.value);
                      setServerError(null);
                      setErrors({});
                    }}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-k-sm px-3 py-2 text-[0.875rem] font-medium transition-colors ${
                      active ? 'bg-white text-k-blue shadow-k-sm' : 'text-k-muted hover:text-k-blue'
                    }`}
                  >
                    <Icon className="size-4" aria-hidden />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {serverError ? (
              <Alert tone="error" className="mt-5">
                {serverError}
              </Alert>
            ) : null}

            <form onSubmit={mode === 'password' ? submitPassword : submitCode} noValidate className="mt-6 space-y-5">
              <Field
                label="Numéro de téléphone"
                htmlFor="login-phone"
                required
                error={errors.phone}
                hint="Le numéro utilisé lors de votre inscription."
              >
                <Input
                  id="login-phone"
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
                />
              </Field>

              {mode === 'password' ? (
                <>
                  <Field label="Mot de passe" htmlFor="login-password" required error={errors.password}>
                    <Input
                      id="login-password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      error={errors.password}
                      placeholder="Votre mot de passe"
                    />
                  </Field>
                  <div className="flex items-center justify-between">
                    <Link to="/mot-de-passe-oublie" className="text-[0.8125rem] font-medium text-k-blue hover:text-k-green-dark">
                      Mot de passe oublié ?
                    </Link>
                  </div>
                  <Button type="submit" block loading={submitting}>
                    Se connecter
                  </Button>
                </>
              ) : codeSent ? (
                <>
                  <Alert tone="info">
                    Un code a été envoyé par SMS au {formatPhone(normalizePhone(phone) ?? phone) || phone}. Il est
                    valable 5 minutes.
                  </Alert>

                  {devCode ? (
                    <Alert tone="warning" title="Environnement de démonstration">
                      Code de test : <strong>{devCode}</strong> (affiché uniquement en développement).
                    </Alert>
                  ) : null}

                  <Field label="Code de connexion" htmlFor="login-code" required error={errors.code} hint="6 chiffres">
                    <Input
                      id="login-code"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      value={code}
                      onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                      error={errors.code}
                      placeholder="000000"
                      className="text-center font-display text-lg tracking-[0.4em]"
                    />
                  </Field>

                  <Button type="submit" block loading={submitting}>
                    Valider et entrer
                  </Button>

                  <button
                    type="button"
                    onClick={requestCode}
                    disabled={submitting || resendIn > 0}
                    className="w-full text-center text-[0.8125rem] text-k-muted disabled:opacity-60"
                  >
                    {resendIn > 0 ? `Nouveau code dans ${resendIn} s` : 'Recevoir un nouveau code'}
                  </button>
                </>
              ) : (
                <>
                  <p className="text-[0.875rem] text-k-muted">
                    Nous vous envoyons un code à 6 chiffres par SMS. Aucun mot de passe à retenir.
                  </p>
                  <Button
                    type="button"
                    block
                    loading={submitting}
                    onClick={requestCode}
                    icon={<Smartphone className="size-4" aria-hidden />}
                  >
                    Recevoir mon code par SMS
                  </Button>
                </>
              )}
            </form>

            <p className="mt-6 border-t border-k-line pt-5 text-center text-[0.8125rem] text-k-muted">
              Un problème pour vous connecter ?{' '}
              <a href="tel:+237600000000" className="font-medium text-k-blue hover:text-k-green-dark">
                Appelez le +237 600 000 000
              </a>
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
