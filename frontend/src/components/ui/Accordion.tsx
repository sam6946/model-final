import { useState, type ReactNode } from 'react';
import clsx from 'clsx';
import { ChevronDown } from 'lucide-react';

export type AccordionItem = {
  id: string | number;
  question: string;
  answer: ReactNode;
};

/** FAQ accessible : bouton natif, état annoncé, hauteur animée en CSS pur. */
export function Accordion({ items, className }: { items: AccordionItem[]; className?: string }) {
  const [openId, setOpenId] = useState<string | number | null>(items[0]?.id ?? null);

  return (
    <div className={clsx('divide-y divide-k-line border-y border-k-line', className)}>
      {items.map((item) => {
        const open = openId === item.id;
        return (
          <div key={item.id}>
            <h3>
              <button
                type="button"
                aria-expanded={open}
                aria-controls={`faq-panel-${item.id}`}
                onClick={() => setOpenId(open ? null : item.id)}
                className="flex w-full items-start justify-between gap-6 py-5 text-left transition-colors hover:text-k-blue"
              >
                <span className="font-display text-[1.0625rem] font-semibold text-k-ink">{item.question}</span>
                <ChevronDown
                  className={clsx(
                    'mt-1 size-4 shrink-0 text-k-muted transition-transform duration-300',
                    open && 'rotate-180 text-k-green',
                  )}
                  aria-hidden
                />
              </button>
            </h3>
            <div
              id={`faq-panel-${item.id}`}
              hidden={!open}
              className="max-w-3xl pb-5 pr-8 text-[0.9375rem] leading-relaxed text-k-muted"
            >
              {item.answer}
            </div>
          </div>
        );
      })}
    </div>
  );
}
