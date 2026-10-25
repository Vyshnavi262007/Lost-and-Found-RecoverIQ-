import { Link } from 'react-router-dom';
import { Bell, ClipboardCheck, ListChecks, PlusCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import useFetch from '../../hooks/useFetch.js';
import { useAuth } from '../../context/AuthContext.jsx';
import ReportCard from '../../components/ReportCard.jsx';
import { EmptyState, ErrorState, PageHeader, Spinner, Stat } from '../../components/ui.jsx';
import { timeAgo } from '../../utils/format.js';

export default function StudentDashboard() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useFetch('/dashboard/student/');
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title={`Hello, ${user.first_name || 'there'}`} subtitle={[user.department, user.year && `Year ${user.year}`, user.campus_name].filter(Boolean).join(' - ') || 'Welcome back to RecoverIQ'}
        actions={<><Link to="/report/new?type=lost" className="btn-primary"><PlusCircle className="h-4 w-4" /> Report lost</Link><Link to="/report/new?type=found" className="btn-secondary"><PlusCircle className="h-4 w-4" /> Report found</Link></>} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Link to="/my-reports"><Stat label="Active reports" value={data.active_reports} /></Link>
        <Link to="/matches"><Stat label="Possible matches" value={data.possible_matches} /></Link>
        <Link to="/my-claims"><Stat label="Pending claims" value={data.pending_claims} /></Link>
        <Stat label="Items recovered" value={data.items_recovered} tone="ok" />
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-1">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Bell className="h-4 w-4" /> Recent notifications</h2>
          {data.recent_notifications.length === 0 ? <EmptyState title="Nothing new" hint="Match alerts and claim updates appear here." /> : (
            <ul className="card divide-y divide-slate-100">
              {data.recent_notifications.map((n) => (
                <li key={n.id}><Link to={n.link || '/notifications'} className={`block px-4 py-3 text-sm hover:bg-slate-50 ${n.is_read ? 'text-slate-500' : ''}`}>
                  <span className="font-medium">{n.title}</span><span className="block text-xs text-slate-500">{timeAgo(n.created_at)}</span></Link></li>
              ))}
            </ul>
          )}
        </section>
        <section className="lg:col-span-2">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><ListChecks className="h-4 w-4" /> Recent community reports</h2>
          {data.recent_reports.length === 0 ? <EmptyState title="No reports yet" /> :
            <div className="grid gap-4 sm:grid-cols-2">{data.recent_reports.slice(0, 4).map((r) => <ReportCard key={r.id} report={r} />)}</div>}
        </section>
      </div>
    </>
  );
}
