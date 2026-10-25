import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Send } from 'lucide-react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { EmptyState, ErrorState, PageHeader, Spinner } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { timeAgo, fmtDateTime } from '../../utils/format.js';

export function MessageList() {
  const { data, loading, error, reload } = useFetch('/conversations/');
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Messages" subtitle="Private conversations about reports." />
      {data.length === 0 ? <EmptyState title="No conversations yet" hint='Open a report and choose "Send private inquiry" to start one.' /> : (
        <ul className="card divide-y divide-slate-100">{data.map((c) => (
          <li key={c.id}><Link to={`/messages/${c.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50">
            <div className="min-w-0 flex-1"><p className="text-sm font-medium">{c.other_name} <span className="font-normal text-slate-500">about {c.report.title}</span></p><p className="truncate text-sm text-slate-500">{c.last_message}</p></div>
            <div className="text-right"><p className="text-xs text-slate-400">{timeAgo(c.last_at)}</p>{c.unread_count > 0 && <span className="mt-1 inline-block rounded-full bg-navy-700 px-2 py-0.5 text-xs text-white">{c.unread_count}</span>}</div></Link></li>))}
        </ul>
      )}
    </>
  );
}

export function Conversation() {
  const { id } = useParams();
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(`/conversations/${id}/`);
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }); window.dispatchEvent(new Event('riq:notifications')); }, [data]);
  const send = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try { await api.post(`/conversations/${id}/messages/`, { body }); setBody(''); reload(); } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  };
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title={data.other_name} subtitle={<>About <Link className="link" to={`/reports/${data.report.id}`}>{data.report.title}</Link></>} actions={<Link to="/messages" className="btn-secondary">All messages</Link>} />
      <div className="card flex h-[60vh] flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {data.messages.map((m) => (
            <div key={m.id} className={`flex ${m.mine ? 'justify-end' : ''}`}><div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${m.mine ? 'bg-navy-800 text-white' : 'bg-slate-100'}`}><p className="whitespace-pre-line">{m.body}</p><p className={`mt-1 text-[10px] ${m.mine ? 'text-navy-200' : 'text-slate-400'}`}>{fmtDateTime(m.created_at)}</p></div></div>
          ))}
          <div ref={end} />
        </div>
        {data.can_reply ? (
          <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3">
            <input className="input" aria-label="Message" placeholder="Write a message" maxLength={2000} value={body} onChange={(e) => setBody(e.target.value)} />
            <button className="btn-primary" disabled={busy || !body.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
          </form>
        ) : <p className="border-t border-slate-200 p-3 text-center text-xs text-slate-500">Moderator view (read-only, access is logged).</p>}
      </div>
    </>
  );
}
