import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import clsx from 'clsx';
import { AlertCircle } from 'lucide-react';

const controlBase =
  'w-full rounded-k border bg-white px-3.5 text-[0.9375rem] text-k-ink transition-colors duration-150 placeholder:text-k-muted/70 focus:outline-none focus:ring-4 disabled:bg-k-mist disabled:text-k-muted';

function stateClasses(error?: string) {
  return error
    ? 'border-k-red focus:border-k-red focus:ring-k-red/12'
    : 'border-k-line hover:border-k-blue-line focus:border-k-blue focus:ring-k-blue/10';
}

type FieldProps = {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
};

/** Enveloppe commune : libellé, indication, message d'erreur lisible. */
export function Field({ label, htmlFor, hint, error, required, children, className }: FieldProps) {
  return (
    <div className={clsx('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-[0.8125rem] font-medium text-k-ink">
        {label}
        {required ? <span className="ml-0.5 text-k-green" aria-hidden> *</span> : null}
        {!required ? <span className="ml-1 font-normal text-k-muted">(facultatif)</span> : null}
      </label>
      {children}
      {hint && !error ? <p className="text-xs leading-relaxed text-k-muted">{hint}</p> : null}
      {error ? (
        <p className="flex items-start gap-1.5 text-[0.8125rem] font-medium text-k-red" role="alert">
          <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      ) : null}
    </div>
  );
}

export type InputProps = InputHTMLAttributes<HTMLInputElement> & { error?: string };

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { error, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      aria-invalid={error ? true : undefined}
      className={clsx(controlBase, stateClasses(error), 'h-11', className)}
      {...rest}
    />
  );
});

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { error?: string };

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { error, className, children, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      aria-invalid={error ? true : undefined}
      className={clsx(controlBase, stateClasses(error), 'h-11 appearance-none pr-9', className)}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%2364748b'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3E%3C/svg%3E\")",
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 0.75rem center',
        backgroundSize: '1.1rem',
      }}
      {...rest}
    >
      {children}
    </select>
  );
});

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { error?: string };

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { error, className, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={error ? true : undefined}
      className={clsx(controlBase, stateClasses(error), 'resize-y py-2.5 leading-relaxed', className)}
      {...rest}
    />
  );
});

/** Groupe de choix (cartes cliquables) — utilisé par les formulaires multi-étapes. */
export function ChoiceGroup<T extends string>({
  options,
  value,
  onChange,
  columns = 2,
  name,
}: {
  options: Array<{ value: T; label: string; description?: string; icon?: ReactNode }>;
  value: T | null;
  onChange: (value: T) => void;
  columns?: 1 | 2 | 3;
  name: string;
}) {
  return (
    <div
      role="radiogroup"
      className={clsx(
        'grid gap-2.5',
        columns === 1 && 'grid-cols-1',
        columns === 2 && 'sm:grid-cols-2',
        columns === 3 && 'sm:grid-cols-2 lg:grid-cols-3',
      )}
    >
      {options.map((option) => {
        const selected = value === option.value;
        return (
          <label
            key={option.value}
            className={clsx(
              'group flex cursor-pointer items-start gap-3 rounded-k border p-3.5 transition-all duration-200',
              selected
                ? 'border-k-green bg-k-green-pale/60 shadow-k-sm'
                : 'border-k-line bg-white hover:border-k-blue-line hover:bg-k-mist',
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={selected}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.icon ? (
              <span
                className={clsx(
                  'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-k-sm',
                  selected ? 'bg-k-green text-white' : 'bg-k-mist text-k-blue',
                )}
                aria-hidden
              >
                {option.icon}
              </span>
            ) : null}
            <span className="flex flex-col gap-0.5">
              <span className="text-[0.9375rem] font-medium text-k-ink">{option.label}</span>
              {option.description ? (
                <span className="text-[0.8125rem] leading-relaxed text-k-muted">{option.description}</span>
              ) : null}
            </span>
          </label>
        );
      })}
    </div>
  );
}

/** Case à cocher avec libellé riche (consentement, options). */
export function Checkbox({
  checked,
  onChange,
  label,
  error,
  name,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: ReactNode;
  error?: string;
  name: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          name={name}
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="mt-0.5 size-5 shrink-0 accent-k-green"
        />
        <span className="text-[0.875rem] leading-relaxed text-k-ink">{label}</span>
      </label>
      {error ? (
        <p className="flex items-center gap-1.5 text-[0.8125rem] font-medium text-k-red" role="alert">
          <AlertCircle className="size-3.5" aria-hidden />
          {error}
        </p>
      ) : null}
    </div>
  );
}
