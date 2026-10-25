import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Bookmark, Calendar, Flag, HandHeart, MapPin, MessageCircle, Pencil, Sparkles, XCircle, ImageOff, Lock } from 'lucide-react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { ConfirmDialog, Modal } from '../../components/Modal.jsx';
import { ErrorState, Field, Spinner, StatusBadge, TypeBadge } from '../../components/ui.jsx';
import { fmtDate, timeAgo } from '../../utils/format.js';

function Comments({ id }) {
  const { data, loading, error, reload } = useFetch(`/reports/${id}/comments/`);
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const post = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try { await api.post(`/reports/${id}/comments/`, { body }); setBody(''); reload(); } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  };
  const del = async (cid) => { try { await api.delete(`/comments/${cid}/`); reload(); } catch (err) { toast.error(errorMessage(err)); } };
  return (
    <section className="card p-5">
      <h2 className="mb-3 font-semibold">Public comments</h2>
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.length === 0 ? <p className="text-sm text-slate-500">No comments yet. Please do not post phone numbers or private details here.</p> : (
        <ul className="mb-4 space-y-3">{data.map((c) => (
          <li key={c.id} className="text-sm"><span className="font-medium">{c.author_name}</span> <span className="text-xs text-slate-400">{timeAgo(c.created_at)}</span>
            {c.can_delete && <button className="ml-2 text-xs text-red-600 hover:underline" onClick={() => del(c.id)}>Delete</button>}
            <p className="text-slate-700">{c.body}</p></li>))}
        </ul>
      )}
      <form onSubmit={post} className="flex gap-2">
        <input className="input" aria-label="Add a comment" placeholder="Add a public comment" maxLength={1000} value={body} onChange={(e) => setBody(e.target.value)} />
        <button className="btn-primary" disabled={busy || !body.trim()}>Post</button>
      </form>
    </section>
  );
}

function ClaimModal({ report, open, onClose }) {
  const nav = useNavigate();
  const toast = useToast();
  const questions = useFetch(open ? '/claims/questions/' : null);
  const [answers, setAnswers] = useState({});
  const [description, setDescription] = useState('');
  const [handover, setHandover] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true); setError('');
    try {
      const list = (questions.data || []).map((q, i) => ({ question: q, answer: answers[i] || '' }));
      const { data } = await api.post('/claims/', { report: report.id, description, answers: list, preferred_handover: handover });
      if (file) {
        const fd = new FormData(); fd.append('file', file);
        try { await api.post(`/claims/${data.id}/evidence/`, fd); } catch (e) { toast.error('Claim sent, but evidence upload failed: ' + errorMessage(e)); }
      }
      toast.success('Claim submitted. A reviewer will verify your answers.');
      nav(`/claims/${data.id}`);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open={open} onClose={onClose} title="Claim this item" footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" onClick={submit} disabled={busy}>{busy ? 'Sending...' : 'Submit claim'}</button></>}>
      <div className="space-y-3">
        <p className="text-sm text-slate-600">Answer from your own knowledge of the item. Hidden details are never shown to claimants; a reviewer compares your answers.</p>
        {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">{error}</p>}
        <Field label="Describe your item"><textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        {(questions.data || []).map((q, i) => <Field key={q} label={q}><textarea className="input" rows={2} value={answers[i] || ''} onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })} /></Field>)}
        <Field label="Preferred handover (optional)"><input className="input" value={handover} onChange={(e) => setHandover(e.target.value)} placeholder="e.g. Security desk after 4 pm" /></Field>
        <Field label="Private evidence (optional)" hint="Photo or PDF, under 5 MB. Only reviewers can open it."><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" onChange={(e) => setFile(e.target.files[0] || null)} /></Field>
      </div>
    </Modal>
  );
}

export default function ReportDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const { data: r, loading, error, reload, setData } = useFetch(`/reports/${id}/`);
  const [img, setImg] = useState(0);
  const [modal, setModal] = useState(null);
  const [msg, setMsg] = useState('');
  const [reason, setReason] = useState('spam');
  const [details, setDetails] = useState('');
  const [busy, setBusy] = useState(false);

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const run = async (fn, ok) => { setBusy(true); try { await fn(); if (ok) toast.success(ok); setModal(null); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); } };
  const toggleBookmark = () => run(async () => {
    await (r.is_bookmarked ? api.delete(`/reports/${r.id}/bookmark/`) : api.post(`/reports/${r.id}/bookmark/`));
    setData({ ...r, is_bookmarked: !r.is_bookmarked });
  });
  const canClaim = r.type === 'found' && !r.is_owner && r.status === 'open' && !r.has_active_claim;
  const isDesk = user.role === 'staff' || user.role === 'admin';
  const privileged = r.is_owner || isDesk;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div className="card overflow-hidden">
          {r.images.length ? (
            <>
              <img src={r.images[img].url} alt={r.title} className="max-h-96 w-full bg-slate-50 object-contain" />
              {r.images.length > 1 && <div className="flex gap-2 p-3">{r.images.map((im, i) => <button key={im.id} onClick={() => setImg(i)} aria-label={`Photo ${i + 1}`}><img src={im.url} alt="" className={`h-14 w-14 rounded object-cover ${i === img ? 'ring-2 ring-navy-600' : ''}`} /></button>)}</div>}
            </>
          ) : <div className="flex h-48 items-center justify-center bg-navy-50 text-navy-300"><ImageOff className="h-10 w-10" /></div>}
          <div className="p-5">
            <div className="mb-2 flex flex-wrap items-center gap-2"><TypeBadge type={r.type} /><StatusBadge status={r.status} />{r.held_by_staff && <span className="rounded-full border border-navy-100 bg-navy-50 px-2 py-0.5 text-xs text-navy-700">Held at campus desk</span>}{r.moderation !== 'approved' && <StatusBadge status={r.moderation} />}</div>
            <h1 className="text-2xl font-semibold">{r.title}</h1>
            <p className="mt-3 whitespace-pre-line text-slate-700">{r.description}</p>
            <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              {[['Category', r.category.name], ['Brand', r.brand], ['Colour', r.color], ['Building / block', r.building], ['Distinguishing features', r.features], ['Notes', r.notes]].filter(([, v]) => v).map(([k, v]) => <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd>{v}</dd></div>)}
            </dl>
            <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
              <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4" /> {r.location.name}</span>
              <span className="flex items-center gap-1.5"><Calendar className="h-4 w-4" /> {fmtDate(r.date)}{r.time ? ` at ${r.time.slice(0, 5)}` : ''}</span>
              <span>{r.type === 'lost' ? 'Owner' : 'Finder'}: {r.reporter_name}</span>
            </div>
          </div>
        </div>
        {privileged && r.private_details && (
          <div className="card border-amber-200 bg-amber-50/40 p-5"><h2 className="mb-1 flex items-center gap-2 font-semibold"><Lock className="h-4 w-4" /> Private identifying details</h2><p className="text-sm text-slate-700">{r.private_details}</p><p className="mt-2 text-xs text-slate-500">Visible only to you and authorised staff.</p></div>
        )}
        <Comments id={r.id} />
      </div>

      <aside className="space-y-3">
        <div className="card space-y-2 p-4">
          {canClaim && <button className="btn-success w-full" onClick={() => setModal('claim')}><HandHeart className="h-4 w-4" /> This is mine - claim item</button>}
          {r.has_active_claim && <Link to="/my-claims" className="btn-secondary w-full">You have a claim on this item</Link>}
          {!r.is_owner && <button className="btn-secondary w-full" onClick={() => setModal('message')}><MessageCircle className="h-4 w-4" /> Send private inquiry</button>}
          <button className="btn-secondary w-full" onClick={toggleBookmark} disabled={busy}><Bookmark className={`h-4 w-4 ${r.is_bookmarked ? 'fill-navy-700' : ''}`} /> {r.is_bookmarked ? 'Bookmarked' : 'Bookmark'}</button>
          {(r.is_owner || isDesk) && <Link to={`/reports/${r.id}/matches`} className="btn-secondary w-full"><Sparkles className="h-4 w-4" /> View possible matches</Link>}
          {r.can_edit && <Link to={`/reports/${r.id}/edit`} className="btn-secondary w-full"><Pencil className="h-4 w-4" /> Edit report</Link>}
          {r.can_edit && r.is_owner && <button className="btn-secondary w-full text-red-700" onClick={() => setModal('close')}><XCircle className="h-4 w-4" /> Close report</button>}
          {!r.is_owner && <button className="btn-ghost w-full text-slate-500" onClick={() => setModal('abuse')}><Flag className="h-4 w-4" /> Report abuse</button>}
        </div>
        {r.type === 'found' && !r.is_owner && <p className="px-1 text-xs text-slate-500">Items are released only after a reviewer verifies ownership.</p>}
      </aside>

      <ClaimModal report={r} open={modal === 'claim'} onClose={() => setModal(null)} />
      <Modal open={modal === 'message'} title="Send a private inquiry" onClose={() => setModal(null)}
        footer={<><button className="btn-secondary" onClick={() => setModal(null)}>Cancel</button><button className="btn-primary" disabled={busy || !msg.trim()} onClick={() => run(async () => { const { data } = await api.post('/conversations/', { report: r.id, body: msg }); nav(`/messages/${data.id}`); }, 'Message sent.')}>Send</button></>}>
        <textarea className="input" rows={4} maxLength={2000} placeholder="Write your message. Don't share private identifying details of an item here." value={msg} onChange={(e) => setMsg(e.target.value)} aria-label="Message" />
      </Modal>
      <Modal open={modal === 'abuse'} title="Report abuse" onClose={() => setModal(null)}
        footer={<><button className="btn-secondary" onClick={() => setModal(null)}>Cancel</button><button className="btn-primary" disabled={busy} onClick={() => run(() => api.post(`/reports/${r.id}/abuse/`, { reason, details }), 'Thanks. A moderator will review this.')}>Submit</button></>}>
        <div className="space-y-3">
          <Field label="Reason"><select className="input" value={reason} onChange={(e) => setReason(e.target.value)}><option value="spam">Spam</option><option value="fake">Fake or misleading</option><option value="inappropriate">Inappropriate</option><option value="private">Shares private info</option><option value="other">Other</option></select></Field>
          <Field label="Details (optional)"><textarea className="input" rows={3} maxLength={500} value={details} onChange={(e) => setDetails(e.target.value)} /></Field>
        </div>
      </Modal>
      <ConfirmDialog open={modal === 'close'} title="Close this report?" message="It will leave the public feed and its possible matches will be removed. This cannot be undone." danger confirmLabel="Close report" busy={busy} onClose={() => setModal(null)}
        onConfirm={() => run(async () => { await api.post(`/reports/${r.id}/close/`); reload(); }, 'Report closed.')} />
    </div>
  );
}
