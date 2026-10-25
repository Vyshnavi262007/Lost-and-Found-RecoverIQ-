import { Link } from 'react-router-dom';
import useFetch from '../../hooks/useFetch.js';
import { ErrorState, PageHeader, Spinner, Stat } from '../../components/ui.jsx';
import { fmtDateTime } from '../../utils/format.js';

export default function AdminDashboard() {
  const { data, loading, error, reload } = useFetch('/admin/analytics/', { days: 30 });
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const t = data.totals;
  return (
    <>
      <PageHeader title="Administrator dashboard" subtitle="Live figures from the database (reports counted for the last 30 days)." actions={<Link to="/admin/analytics" className="btn-secondary">Full analytics</Link>} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Link to="/admin/users"><Stat label="Registered users" value={t.users} /></Link>
        <Stat label="Lost reports" value={t.lost_reports} />
        <Stat label="Found reports" value={t.found_reports} />
        <Stat label="Items returned" value={t.items_returned} tone="ok" />
        <Link to="/admin/disputes"><Stat label="Open disputes" value={t.open_disputes} /></Link>
        <Link to="/admin/abuse"><Stat label="Open abuse reports" value={t.open_abuse_reports} /></Link>
        <Stat label="Pending claims" value={t.pending_claims} />
        <Stat label="Items in storage" value={t.inventory_in_storage} />
      </div>
      <h2 className="mb-3 mt-8 font-semibold">Recent audit events</h2>
      {data.recent_audit.length === 0 ? <p className="text-sm text-slate-500">No activity yet.</p> : (
        <ul className="card divide-y divide-slate-100 text-sm">{data.recent_audit.map((a) => <li key={a.id} className="flex justify-between gap-3 px-4 py-2"><span><b>{a.action}</b> <span className="text-slate-500">{a.actor_name}</span></span><span className="text-xs text-slate-400">{fmtDateTime(a.created_at)}</span></li>)}</ul>
      )}
    </>
  );
}
