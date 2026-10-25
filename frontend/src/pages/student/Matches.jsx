import { Link, useParams } from 'react-router-dom';
import { ImageOff, MapPin, Calendar } from 'lucide-react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { useToast } from '../../context/ToastContext.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import { EmptyState, ErrorState, PageHeader, Spinner, TypeBadge, Pagination } from '../../components/ui.jsx';
import { fmtDate } from '../../utils/format.js';
import { useState } from 'react';
import { unwrap } from '../../utils/format.js';

const LABELS = { category: 'Category', text: 'Description', location: 'Location', date: 'Date', visual: 'Photo' };

function MatchCard({ m, mineId, onDismiss }) {
  const { user } = useAuth();
  const other = m.lost_report.id === mineId || (mineId == null && m.lost_report.is_owner) ? m.found_report : m.lost_report;
  const mine = other === m.found_report ? m.lost_report : m.found_report;
  return (
    <article className="card flex flex-col gap-4 p-4 sm:flex-row">
      {other.thumbnail ? <img src={other.thumbnail} alt={other.title} className="h-28 w-full rounded-lg object-cover sm:w-36" /> : <div className="flex h-28 w-full items-center justify-center rounded-lg bg-navy-50 text-navy-300 sm:w-36"><ImageOff className="h-7 w-7" /></div>}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2"><TypeBadge type={other.type} /><h3 className="font-medium">{other.title}</h3></div>
        <p className="mt-1 text-xs text-slate-500">Matches your {mine.type} report: <Link className="link" to={`/reports/${mine.id}`}>{mine.title}</Link></p>
        <p className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500"><span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{other.location.name}</span><span className="flex items-center gap-1"><Calendar className="h-3.5 w-3.5" />{fmtDate(other.date)}</span></p>
        <p className="mt-2 text-sm text-slate-700">{m.explanation}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">{Object.entries(m.components).filter(([, c]) => c.score != null).map(([k, c]) => <span key={k} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{LABELS[k]} {Math.round(c.score * 100)}%</span>)}</div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to={`/reports/${other.id}`} className="btn-primary btn-sm">Open report</Link>
          {other.type === 'found' && user.id && <Link to={`/reports/${other.id}`} className="btn-success btn-sm">Claim or contact</Link>}
          {other.type === 'lost' && <Link to={`/reports/${other.id}`} className="btn-secondary btn-sm">Contact owner</Link>}
          <button className="btn-ghost btn-sm" onClick={() => onDismiss(m.id)}>Dismiss match</button>
        </div>
      </div>
      <div className="text-center sm:w-28"><p className="text-2xl font-semibold text-navy-800">{m.similarity_estimate}%</p><p className="text-xs text-slate-500">Similarity estimate</p></div>
    </article>
  );
}

function List({ items, mineId, onDismiss, empty }) {
  if (!items.length) return <EmptyState title="No possible matches right now" hint={empty} />;
  return <div className="space-y-4">{items.map((m) => <MatchCard key={m.id} m={m} mineId={mineId} onDismiss={onDismiss} />)}</div>;
}

export function ReportMatches() {
  const { id } = useParams();
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(`/reports/${id}/matches/`);
  const dismiss = async (mid) => { try { await api.post(`/matches/${mid}/dismiss/`); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (<><PageHeader title="Possible matches" subtitle="Similarity estimates are suggestions, not a guarantee of identity." actions={<Link to={`/reports/${id}`} className="btn-secondary">Back to report</Link>} />
    <List items={data} mineId={Number(id)} onDismiss={dismiss} empty="We keep checking as new reports arrive. You will get a notification for strong matches." /></>);
}

export function AllMatches() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/matches/', { page });
  const dismiss = async (mid) => { try { await api.post(`/matches/${mid}/dismiss/`); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (<><PageHeader title="Smart matches" subtitle="Possible matches for your reports, highest similarity first. These are estimates only." />
    <List items={unwrap(data)} onDismiss={dismiss} empty="Report a lost or found item and we will look for matches." />
    <Pagination data={data} page={page} onPage={setPage} /></>);
}
