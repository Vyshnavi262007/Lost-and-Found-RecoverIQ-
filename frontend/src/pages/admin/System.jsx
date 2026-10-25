import { useEffect, useState } from 'react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { EmptyState, ErrorState, Field, PageHeader, Pagination, Spinner } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { fmtDateTime } from '../../utils/format.js';

export function AuditLogs() {
  const [f, setF] = useState({ action: '', q: '', page: 1 });
  const { data, loading, error, reload } = useFetch('/admin/audit-logs/', f);
  return (
    <>
      <PageHeader title="Audit logs" subtitle="Sensitive actions: claim decisions, handovers, admin changes, moderation." />
      <div className="card mb-4 flex flex-wrap gap-3 p-3"><input className="input max-w-xs" placeholder="Action contains (e.g. claim.)" aria-label="Action" value={f.action} onChange={(e) => setF({ ...f, action: e.target.value, page: 1 })} /><input className="input max-w-xs" placeholder="Actor email or target type" aria-label="Actor" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} /></div>
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No matching events" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr><th className="th">When</th><th className="th">Actor</th><th className="th">Action</th><th className="th">Target</th><th className="th">Detail</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.results.map((a) => <tr key={a.id}><td className="td whitespace-nowrap">{fmtDateTime(a.created_at)}</td><td className="td">{a.actor_name}</td><td className="td font-medium">{a.action}</td><td className="td">{a.target_type} {a.target_id && `#${a.target_id}`}</td><td className="td max-w-xs truncate text-xs text-slate-500">{Object.keys(a.detail || {}).length ? JSON.stringify(a.detail) : ''}</td></tr>)}</tbody></table></div>
      )}
      <Pagination data={data} page={f.page} onPage={(p) => setF({ ...f, page: p })} />
    </>
  );
}

const W = ['category', 'text', 'location', 'date', 'visual'];

export function SystemSettings() {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch('/admin/settings/');
  const [s, setS] = useState(null);
  useEffect(() => { if (data) setS(data); }, [data]);
  if (loading || !s) return error ? <ErrorState message={error} onRetry={reload} /> : <Spinner />;
  const save = async () => { try { await api.patch('/admin/settings/', s); toast.success('Settings saved. New matches use them immediately.'); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  const total = W.reduce((a, k) => a + Number(s.match_weights[k] || 0), 0);
  return (
    <>
      <PageHeader title="System settings" actions={<button className="btn-primary" onClick={save}>Save settings</button>} />
      <div className="grid max-w-4xl gap-6 md:grid-cols-2">
        <section className="card space-y-3 p-5"><h2 className="font-semibold">Matching weights</h2>
          <p className="text-xs text-slate-500">Relative weights (they are renormalised, currently summing to {total.toFixed(2)}). The visual weight only applies when the optional image model is installed.</p>
          {W.map((k) => <Field key={k} label={k[0].toUpperCase() + k.slice(1)}><input type="number" step="0.05" min="0" className="input" value={s.match_weights[k]} onChange={(e) => setS({ ...s, match_weights: { ...s.match_weights, [k]: Number(e.target.value) } })} /></Field>)}
          <Field label="Minimum match threshold (0-1)"><input type="number" step="0.05" min="0" max="1" className="input" value={s.match_threshold} onChange={(e) => setS({ ...s, match_threshold: Number(e.target.value) })} /></Field>
          <Field label="Notify at similarity of (0-1)"><input type="number" step="0.05" min="0" max="1" className="input" value={s.match_notify_threshold} onChange={(e) => setS({ ...s, match_notify_threshold: Number(e.target.value) })} /></Field></section>
        <section className="card space-y-3 self-start p-5"><h2 className="font-semibold">Reports and notifications</h2>
          <Field label="Report expiry (days)" hint="Applied by the expire_reports command (schedule it daily)."><input type="number" min="1" className="input" value={s.report_expiry_days} onChange={(e) => setS({ ...s, report_expiry_days: Number(e.target.value) })} /></Field>
          {[['require_report_approval', 'Student reports need approval before appearing publicly'], ['notify_on_match', 'In-app notifications for matches'], ['notify_on_comment', 'In-app notifications for comments'], ['notify_on_message', 'In-app notifications for messages']].map(([k, label]) => <label key={k} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!s[k]} onChange={(e) => setS({ ...s, [k]: e.target.checked })} /> {label}</label>)}</section>
      </div>
    </>
  );
}
