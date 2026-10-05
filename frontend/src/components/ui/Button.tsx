import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { Loader2 } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
type Size = 'sm' | 'md' | 'lg';

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-k-blue text-white border border-k-blue hover:bg-k-blue-dark hover:border-k-blue-dark active:translate-y-px',
  secondary:
    'bg-white text-k-ink border border-k-line hover:border-k-blue-line hover:bg-k-mist active:translate-y-px',
  ghost: 'bg-transparent text-k-blue border border-transparent hover:bg-k-blue-soft/70',
  danger: 'bg-k-red text-white border border-k-red hover:brightness-95 active:translate-y-px',
  success:
    'bg-k-green text-white border border-k-green hover:bg-k-green-dark hover:border-k-green-dark active:translate-y-px',
};

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3.5 text-[0.8125rem] gap-1.5',
  md: 'h-11 px-5 text-[0.9375rem] gap-2',
  lg: 'h-13 px-6 text-base gap-2.5',
};

type CommonProps = {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  iconRight?: ReactNode;
  block?: boolean;
  className?: string;
  children?: ReactNode;
};

export type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>;

const base =
  'inline-flex items-center justify-center rounded-k font-medium transition-all duration-200 disabled:opacity-55 disabled:pointer-events-none whitespace-nowrap';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, icon, iconRight, block, className, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={clsx(base, VARIANTS[variant], SIZES[size], block && 'w-full', className)}
      disabled={rest.disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
      {!loading && iconRight}
    </button>
  );
});

type LinkButtonProps = CommonProps & {
  to: string;
  state?: unknown;
  target?: string;
  rel?: string;
  onClick?: () => void;
  'aria-label'?: string;
};

/** Même apparence que le bouton, mais rendu comme un lien (navigation réelle, SEO). */
export function ButtonLink({
  to,
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  block,
  className,
  children,
  ...rest
}: LinkButtonProps) {
  return (
    <Link
      to={to}
      className={clsx(base, VARIANTS[variant], SIZES[size], block && 'w-full', className)}
      {...rest}
    >
      {icon}
      {children}
      {iconRight}
    </Link>
  );
}
