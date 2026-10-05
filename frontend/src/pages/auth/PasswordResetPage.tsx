import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, KeyRound, ShieldCheck, Smartphone } from 'lucide-react';

import { http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert } from '@/components/ui/Feedback';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Field';
import { ProgressSteps } from '@/components/ui/Steps';
import { normalizePhone, passwordStrength } from '@/lib/validators';
import { formatPhone } from '@/lib/format';

const STEPS = ['Téléphone', 'Code SMS', 'Nouveau mot de passe'];

export default function PasswordResetPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [ticket, setTicket] = useState<string | null>(null);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const requestCode = async (event?: React.FormEvent) => {
    event?.preventDefault();
    setServerError(null);
    const normalized = normalizePhone(phone);
    if (!normalized) {
      setErrors({ phone: 'Veuillez renseigner un numéro de téléphone valide.' });
      return;
    }
    setSubmitting(true);
    try {
      const data = await http.post<{ dev_code?: string }>('/auth/password/reset/', { phone: normalized });
      setDevCode(data.dev_code ?? null);
      setErrors({});
      setStep(2);
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? "La demande n'a pas abouti. Vérifiez le numéro puis réessayez.");
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
        purpose: 'PASSWORD_RESET',
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

  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);

    const next: Record<string, string> = {};
    if (password.length < 8) next.password = 'Choisissez un mot de passe d\'au moins 8 caractères.';
    if (password !== passwordConfirm) next.password_confirm = 'Les deux mots de passe ne correspondent pas.';
    setErrors(next);
    if (Object.keys(next).length) return;

    const normalized = normalizePhone(phone);
    if (!normalized || !ticket) {
      setServerError('La vérification a expiré. Reprenez depuis le début.');
      setStep(1);
      return;
    }

    setSubmitting(true);
    try {
      await http.post('/auth/password/reset/confirm/', {
        phone: normalized,
        verification_ticket: ticket,
        password,
        password_confirm: passwordConfirm,
      });
      setDone(true);
    } catch (error) {
      const apiError = error as { message?: string; fields?: Record<string, string[]> };
      setServerError(apiError.message ?? 'Le mot de passe n\'a pas pu être modifié.');
      if (apiError.fields) {
        setErrors(Object.fromEntries(Object.entries(apiError.fields).map(([key, value]) => [key, value[0]])));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const strength = passwordStrength(password);

  return (
    <>
      <Seo
        title="Réinitialiser mon mot de passe"
        description="Réinitialisez le mot de passe de votre compte KEMTA par code SMS : trois étapes, aucune donnée sensible transmise par message."
        path="/mot-de-passe-oublie"
        noIndex
      />

      <section className="bg-k-mist">
        <div className="k-container flex justify-center py-14 lg:py-20">
          <div className="w-full max-w-xl">
            <h1 className="text-[1.75rem]">Mot de passe oublié</h1>
            <p className="k-lead mt-3 text-[0.9375rem]">
              Nous vérifions votre identité par un code SMS, puis vous choisissez un nouveau mot de passe. Nous ne
              transmettons jamais de mot de passe par message.
            </p>

            <div className="mt-8 rounded-k-xl border border-k-line bg-white p-6 sm:p-8">
              {done ? (
                <div className="space-y-5">
                  <Alert tone="success" title="Mot de passe modifié">
                    Votre nouveau mot de passe est actif. Vous pouvez vous connecter dès maintenant, par mot de passe
                    ou par code SMS.
                  </Alert>
                  <Button block onClick={() => navigate('/connexion', { replace: true })}>
                    Aller à la connexion
                  </Button>
                </div>
              ) : (
                <>
                  <ProgressSteps steps={STEPS} current={step} />

                  {serverError ? (
                    <Alert tone="error" className="mt-6">
                      {serverError}
                    </Alert>
                  ) : null}

                  {step === 1 ? (
                    <form onSubmit={requestCode} noValidate className="mt-7 space-y-5">
                      <div>
                        <h2 className="text-[1.125rem]">Votre numéro de téléphone</h2>
                        <p className="mt-1.5 text-[0.875rem] text-k-muted">
                          Saisissez le numéro associé à votre compte KEMTA.
                        </p>
                      </div>
                      <Field label="Téléphone" htmlFor="reset-phone" required error={errors.phone}>
                        <Input
                          id="reset-phone"
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
                      <Button type="submit" block loading={submitting} icon={<Smartphone className="size-4" aria-hidden />}>
                        Recevoir un code
                      </Button>
                    </form>
                  ) : null}

                  {step === 2 ? (
                    <form onSubmit={verifyCode} noValidate className="mt-7 space-y-5">
                      <div>
                        <h2 className="text-[1.125rem]">Code de vérification</h2>
                        <p className="mt-1.5 text-[0.875rem] text-k-muted">
                          Code envoyé au {formatPhone(normalizePhone(phone) ?? phone) || phone}.
                        </p>
                      </div>

                      {devCode ? (
                        <Alert tone="warning" title="Environnement de démonstration">
                          Code de test : <strong>{devCode}</strong>
                        </Alert>
                      ) : null}

                      <Field label="Code à 6 chiffres" htmlFor="reset-code" required error={errors.code}>
                        <Input
                          id="reset-code"
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
                        Vérifier le code
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
                    <form onSubmit={changePassword} noValidate className="mt-7 space-y-5">
                      <div>
                        <h2 className="text-[1.125rem]">Nouveau mot de passe</h2>
                        <p className="mt-1.5 text-[0.875rem] text-k-muted">
                          Choisissez un mot de passe que vous n&apos;utilisez pas ailleurs.
                        </p>
                      </div>

                      <Field label="Nouveau mot de passe" htmlFor="reset-password" required error={errors.password}>
                        <Input
                          id="reset-password"
                          type="password"
                          autoComplete="new-password"
                          value={password}
                          onChange={(event) => setPassword(event.target.value)}
                          error={errors.password}
                          placeholder="••••••••"
                          autoFocus
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

                      <Field label="Confirmer" htmlFor="reset-password-2" required error={errors.password_confirm}>
                        <Input
                          id="reset-password-2"
                          type="password"
                          autoComplete="new-password"
                          value={passwordConfirm}
                          onChange={(event) => setPasswordConfirm(event.target.value)}
                          error={errors.password_confirm}
                          placeholder="••••••••"
                        />
                      </Field>

                      <Button type="submit" block loading={submitting} icon={<KeyRound className="size-4" aria-hidden />}>
                        Modifier mon mot de passe
                      </Button>
                    </form>
                  ) : null}
                </>
              )}

              <div className="mt-6 flex items-center justify-between border-t border-k-line pt-5 text-[0.8125rem]">
                <Link to="/connexion" className="text-k-blue hover:text-k-green-dark">
                  Revenir à la connexion
                </Link>
                <span className="inline-flex items-center gap-1.5 text-k-muted">
                  <ShieldCheck className="size-3.5 text-k-green" aria-hidden />
                  Vérification par SMS
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
