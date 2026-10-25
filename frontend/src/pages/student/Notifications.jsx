import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CheckCheck } from 'lucide-react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { timeAgo } from '../../utils/format.js';

export default function Notifications() {
  const [page, setPage] = useState(1);
  const nav = useNavigate();
  const toast = useToast();
  const { data, loading, error, reload } = useFetch('/notifications/', { page });
  const ping = () => window.dispatchEvent(new Event('riq:notifications'));
  const open = async (n) => {
    if (!n.is_read) { try { await api.post(`/notifications/${n.id}/read/`); ping(); } catch { /* ignore */ } }
    if (n.link) nav(n.link); else reload();
  };
  const readAll = async () => { try { await api.post('/notifications/read-all/'); ping(); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Notifications" actions={<button className="btn-secondary" onClick={readAll}><CheckCheck className="h-4 w-4" /> Mark all as read</button>} />
      {data.results.length === 0 ? <EmptyState title="You're all caught up" hint="Matches, comments, messages and claim updates will appear here." /> : (
        <ul className="card divide-y divide-slate-100">
          {data.results.map((n) => (
            <li key={n.id}><button onClick={() => open(n)} className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-slate-50">
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? 'bg-transparent' : 'bg-navy-600'}`} aria-label={n.is_read ? 'Read' : 'Unread'} />
              <span className="min-w-0 flex-1"><span className={`block text-sm ${n.is_read ? 'text-slate-600' : 'font-medium'}`}>{n.title}</span>{n.body && <span className="block truncate text-sm text-slate-500">{n.body}</span>}</span>
              <span className="shrink-0 text-xs text-slate-400">{timeAgo(n.created_at)}</span></button></li>
          ))}
        </ul>
      )}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}
