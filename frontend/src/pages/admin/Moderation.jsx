import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { ConfirmDialog } from '../../components/Modal.jsx';
import { EmptyState, ErrorState, Field, PageHeader, Pagination, Spinner, StatusBadge, Tabs, TypeBadge } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { fmtDate } from '../../utils/format.js';

export function Moderation() {
  const toast = useToast();
  const [tab, setTab] = useState('pending');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [target, setTarget] = useState(null);
  const reports = useFetch(tab === 'duplicates' ? null : '/admin/reports/', { moderation: tab, q, page });
  const dups = useFetch(tab === 'duplicates' ? '/admin/duplicates/' : null);
  const set = async (r, moderation) => { try { await api.post(`/admin/reports/${r.id}/moderate/`, { moderation }); toast.success(`Report ${moderation}.`); setTarget(null); reports.reload(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title="Report moderation" subtitle="Review pending, removed and possibly duplicate reports." />
      <Tabs tabs={[['pending', 'Pending review'], ['approved', 'Approved'], ['removed', 'Removed'], ['duplicates', 'Possible duplicates']]} value={tab} onChange={(t) => { setTab(t); setPage(1); }} />
      {tab === 'duplicates' ? (dups.loading ? <Spinner /> : dups.error ? <ErrorState message={dups.error} onRetry={dups.reload} /> : dups.data.length === 0 ? <EmptyState title="No likely duplicates" hint="Pairs of open reports by one person with very similar text appear here." /> : (
        <ul className="card divide-y divide-slate-100 text-sm">{dups.data.map((p, i) => <li key={i} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3"><span>{p.reporter}: <Link className="link" to={`/reports/${p.a.id}`}>{p.a.title}</Link> and <Link className="link" to={`/reports/${p.b.id}`}>{p.b.title}</Link></span><span className="text-xs text-slate-500">{Math.round(p.similarity * 100)}% text similarity</span></li>)}</ul>
      )) : (
        <>
          <input className="input mb-4 max-w-sm" placeholder="Search reports" aria-label="Search reports" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
          {reports.loading && !reports.data ? <Spinner /> : reports.error ? <ErrorState message={reports.error} onRetry={reports.reload} /> : reports.data.results.length === 0 ? <EmptyState title="Nothing here" /> : (
            <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr><th className="th">Report</th><th className="th">By</th><th className="th">Posted</th><th className="th">State</th><th className="th" /></tr></thead>
              <tbody className="divide-y divide-slate-100">{reports.data.results.map((r) => (
                <tr key={r.id}><td className="td"><TypeBadge type={r.type} /> <Link className="link" to={`/reports/${r.id}`}>{r.title}</Link></td><td className="td">{r.reporter_name}</td><td className="td">{fmtDate(r.created_at)}</td><td className="td"><StatusBadge status={r.moderation} /></td>
                  <td className="td text-right">{r.moderation !== 'approved' && <button className="btn-success btn-sm mr-2" onClick={() => set(r, 'approved')}>Approve</button>}{r.moderation !== 'removed' && <button className="btn-danger btn-sm" onClick={() => setTarget(r)}>Remove</button>}</td></tr>))}</tbody></table></div>
          )}
          <Pagination data={reports.data} page={page} onPage={setPage} />
        </>
      )}
      <ConfirmDialog open={!!target} danger title="Remove this report?" message="It disappears from the feed and matching. The reporter is notified. You can restore it later." confirmLabel="Remove" onClose={() => setTarget(null)} onConfirm={() => set(target, 'removed')} />
    </>
  );
}

export function AbuseReports() {
  const toast = useToast();
  const [status, setStatus] = useState('open');
  const { data, loading, error, reload } = useFetch('/admin/abuse/', { status });
  const act = async (a, action) => { try { await api.post(`/admin/abuse/${a.id}/`, { action }); toast.success('Abuse report updated.'); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title="Abuse reports" />
      <Tabs tabs={[['open', 'Open'], ['resolved', 'Resolved'], ['dismissed', 'Dismissed']]} value={status} onChange={setStatus} />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.length === 0 ? <EmptyState title="No abuse reports" /> : (
        <ul className="space-y-3">{data.map((a) => (
          <li key={a.id} className="card p-4 text-sm"><p><b>{a.reason}</b> reported by {a.reporter}</p>{a.report_id && <p>On <Link className="link" to={`/reports/${a.report_id}`}>{a.report_title}</Link></p>}{a.comment_body && <p className="mt-1 rounded bg-slate-50 p-2">Comment: {a.comment_body}</p>}{a.details && <p className="mt-1 text-slate-600">{a.details}</p>}
            {a.status === 'open' && <div className="mt-3 flex gap-2"><button className="btn-danger btn-sm" onClick={() => act(a, 'remove_content')}>Remove content</button><button className="btn-secondary btn-sm" onClick={() => act(a, 'resolve')}>Mark resolved</button><button className="btn-ghost btn-sm" onClick={() => act(a, 'dismiss')}>Dismiss</button></div>}</li>))}</ul>
      )}
    </>
  );
}

export function Disputes() {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch('/admin/disputes/');
  const [target, setTarget] = useState(null);
  const [note, setNote] = useState('');
  const resolve = async (outcome) => { try { await api.post(`/admin/disputes/${target.id}/`, { outcome, note }); toast.success('Dispute resolved.'); setTarget(null); setNote(''); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Claim disputes" subtitle="Claimants who asked for a rejected claim to be reviewed again." />
      {data.length === 0 ? <EmptyState title="No open disputes" /> : (
        <ul className="space-y-3">{data.map((c) => (
          <li key={c.id} className="card p-4 text-sm"><p><Link className="link" to={`/claims/${c.id}`}>Claim #{c.id}</Link> on {c.report.title} by {c.claimant_name}</p><p className="mt-1 text-slate-600">Rejected: {c.decision_reason}</p><p className="mt-1">Dispute: {c.dispute_note}</p>
            <button className="btn-primary btn-sm mt-3" onClick={() => setTarget(c)}>Resolve</button></li>))}</ul>
      )}
      <ConfirmDialog open={!!target} title="Resolve dispute" confirmLabel="Uphold rejection" onClose={() => setTarget(null)} onConfirm={() => resolve('uphold')}>
        <Field label="Resolution note"><textarea className="input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <button className="btn-secondary mt-3" onClick={() => resolve('reopen')}>Reopen claim for review instead</button>
      </ConfirmDialog>
    </>
  );
}
