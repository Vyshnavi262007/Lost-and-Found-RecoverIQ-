import { AlertCircle, ChevronLeft, ChevronRight, Inbox, Loader2 } from 'lucide-react';
import { STATUS_LABELS } from '../utils/format.js';

const TONES = {
  open: 'bg-navy-50 text-navy-700 border-navy-100', claim_pending: 'bg-amber-50 text-amber-700 border-amber-100',
  returned: 'bg-ok-50 text-ok-700 border-ok-100', completed: 'bg-ok-50 text-ok-700 border-ok-100', approved: 'bg-ok-50 text-ok-700 border-ok-100',
  pending: 'bg-slate-100 text-slate-600 border-slate-200', under_review: 'bg-amber-50 text-amber-700 border-amber-100',
  rejected: 'bg-red-50 text-red-700 border-red-100', withdrawn: 'bg-slate-100 text-slate-500 border-slate-200',
  closed: 'bg-slate-100 text-slate-500 border-slate-200', expired: 'bg-slate-100 text-slate-500 border-slate-200',
  stored: 'bg-navy-50 text-navy-700 border-navy-100', scheduled: 'bg-amber-50 text-amber-700 border-amber-100',
  cancelled: 'bg-slate-100 text-slate-500 border-slate-200', disposed: 'bg-slate-100 text-slate-500 border-slate-200', removed: 'bg-red-50 text-red-700 border-red-100',
  lost: 'bg-red-50 text-red-700 border-red-100', found: 'bg-ok-50 text-ok-700 border-ok-100',
};

export function StatusBadge({ status, label }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${TONES[status] || TONES.pending}`}>
      {label || STATUS_LABELS[status] || status}
    </span>
  );
}

export const TypeBadge = ({ type }) => <StatusBadge status={type} label={type === 'lost' ? 'Lost' : 'Found'} />;

export function Spinner({ label = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function CardSkeletons({ count = 6 }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card animate-pulse overflow-hidden">
          <div className="h-36 bg-slate-100" />
          <div className="space-y-2 p-4"><div className="h-4 w-2/3 rounded bg-slate-100" /><div className="h-3 w-full rounded bg-slate-100" /><div className="h-3 w-1/2 rounded bg-slate-100" /></div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, hint, action, icon: Icon = Inbox }) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      <Icon className="mb-3 h-8 w-8 text-navy-300" />
      <h3 className="font-medium">{title}</h3>
      {hint && <p className="mt-1 max-w-md text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="card flex flex-col items-center border-red-200 px-6 py-10 text-center" role="alert">
      <AlertCircle className="mb-2 h-7 w-7 text-red-500" />
      <p className="text-sm text-slate-700">{message}</p>
      {onRetry && <button className="btn-secondary mt-4" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Field({ label, error, hint, children, htmlFor }) {
  return (
    <div>
      {label && <label htmlFor={htmlFor} className="label">{label}</label>}
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600" role="alert">{error}</p>}
    </div>
  );
}

export function Stat({ label, value, hint, tone }) {
  return (
    <div className="card p-4">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone === 'ok' ? 'text-ok-600' : 'text-navy-900'}`}>{value ?? '-'}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export function Pagination({ data, page, onPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  return (
    <div className="mt-6 flex items-center justify-between text-sm text-slate-600">
      <span>{data.count} results</span>
      <div className="flex items-center gap-2">
        <button className="btn-secondary btn-sm" disabled={!data.previous} onClick={() => onPage(page - 1)}><ChevronLeft className="h-4 w-4" /> Previous</button>
        <span>Page {page}</span>
        <button className="btn-secondary btn-sm" disabled={!data.next} onClick={() => onPage(page + 1)}>Next <ChevronRight className="h-4 w-4" /></button>
      </div>
    </div>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist">
      {tabs.map(([key, label]) => (
        <button key={key} role="tab" aria-selected={value === key} onClick={() => onChange(key)}
          className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${value === key ? 'border-navy-700 text-navy-800' : 'border-transparent text-slate-500 hover:text-navy-700'}`}>
          {label}
        </button>
      ))}
    </div>
  );
}
