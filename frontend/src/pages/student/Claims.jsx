import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle2, Circle, Download, XCircle } from 'lucide-react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { useToast } from '../../context/ToastContext.jsx';
import { ConfirmDialog, Modal } from '../../components/Modal.jsx';
import { EmptyState, ErrorState, Field, PageHeader, Pagination, Spinner, StatusBadge } from '../../components/ui.jsx';
import { fmtDateTime, fmtDate } from '../../utils/format.js';

export function ClaimRow({ c }) {
  return (
    <li><Link to={`/claims/${c.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50">
      <div className="min-w-0 flex-1"><p className="text-sm font-medium">{c.report.title}</p><p className="text-xs text-slate-500">Claim #{c.id} by {c.claimant_name} - {fmtDate(c.created_at)}</p></div>
      <StatusBadge status={c.status} />
    </Link></li>
  );
}

export function MyClaims() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/claims/', { page });
  return (
    <>
      <PageHeader title="My claims" subtitle="Track ownership claims you have submitted." />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? (
        <EmptyState title="No claims yet" hint='Open a found-item report and choose "This is mine" to start a claim.' action={<Link to="/feed?type=found" className="btn-primary">Browse found items</Link>} />
      ) : <ul className="card divide-y divide-slate-100">{data.results.map((c) => <ClaimRow key={c.id} c={c} />)}</ul>}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}

const STEPS = ['pending', 'under_review', 'approved', 'completed'];

function Timeline({ claim }) {
  const reached = new Set(claim.events.map((e) => e.status));
  const ended = ['rejected', 'withdrawn'].find((s) => reached.has(s));
  const steps = ended ? ['pending', 'under_review', ended].filter((s) => s === ended || reached.has(s)) : STEPS;
  return (
    <ol className="space-y-3">
      {steps.map((s) => {
        const hit = claim.events.filter((e) => e.status === s);
        const done = reached.has(s);
        return (
          <li key={s} className="flex gap-3">
            {done ? (s === 'rejected' || s === 'withdrawn' ? <XCircle className="mt-0.5 h-5 w-5 text-red-500" /> : <CheckCircle2 className="mt-0.5 h-5 w-5 text-ok-600" />) : <Circle className="mt-0.5 h-5 w-5 text-slate-300" />}
            <div className="text-sm"><p className={done ? 'font-medium' : 'text-slate-400'}>{s === 'under_review' ? 'Under review' : s[0].toUpperCase() + s.slice(1)}</p>
              {hit.map((e, i) => <p key={i} className="text-xs text-slate-500">{fmtDateTime(e.at)} - {e.actor}{e.note ? `: ${e.note}` : ''}</p>)}</div>
          </li>
        );
      })}
    </ol>
  );
}

export function ClaimDetail() {
  const { id } = useParams();
  const toast = useToast();
  const { data: c, loading, error, reload } = useFetch(`/claims/${id}/`);
  const [modal, setModal] = useState(null);
  const [text, setText] = useState('');
  const [when, setWhen] = useState('');
  const [where, setWhere] = useState('');
  const [busy, setBusy] = useState(false);
  if (loading && !c) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const act = async (path, body, ok) => {
    setBusy(true);
    try { await api.post(`/claims/${id}/${path}/`, body); toast.success(ok); setModal(null); setText(''); reload(); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  };
  const download = async (ev) => {
    try {
      const res = await api.get(`/claim-evidence/${ev.id}/download/`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = ev.name; a.click(); URL.revokeObjectURL(url);
    } catch (e) { toast.error(errorMessage(e)); }
  };
  const upload = async (file) => {
    const fd = new FormData(); fd.append('file', file);
    try { await api.post(`/claims/${id}/evidence/`, fd); toast.success('Evidence uploaded.'); reload(); } catch (e) { toast.error(errorMessage(e)); }
  };
  const doHandover = async () => {
    setBusy(true);
    try { await api.post(`/claims/${id}/handover/`, { scheduled_for: new Date(when).toISOString(), location: where }); toast.success('Handover scheduled.'); setModal(null); reload(); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  };
  const confirmHandover = async (hid) => { try { await api.post(`/handovers/${hid}/confirm/`); toast.success('Handover confirmed. Item marked as returned.'); reload(); } catch (e) { toast.error(errorMessage(e)); } };

  const scheduled = c.handovers.find((h) => h.status === 'scheduled');
  return (
    <>
      <PageHeader title={`Claim #${c.id}`} subtitle={<>For <Link className="link" to={`/reports/${c.report.id}`}>{c.report.title}</Link> - {c.report.location}</>} actions={<StatusBadge status={c.status} />} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="card p-5">
            <h2 className="mb-2 font-semibold">Ownership statement</h2>
            <p className="text-xs text-slate-500">From {c.claimant_name}{c.claimant_student_id ? ` (ID ${c.claimant_student_id})` : ''}</p>
            <p className="mt-2 text-sm">{c.description}</p>
            <dl className="mt-3 space-y-2 text-sm">{c.answers.map((a, i) => <div key={i}><dt className="text-xs text-slate-500">{a.question}</dt><dd>{a.answer}</dd></div>)}</dl>
            {c.preferred_handover && <p className="mt-3 text-sm"><span className="text-xs text-slate-500">Preferred handover: </span>{c.preferred_handover}</p>}
            {c.decision_reason && <p className="mt-3 rounded bg-slate-50 p-2 text-sm"><b>Decision note:</b> {c.decision_reason}</p>}
          </section>
          {c.can_review && (
            <section className="card border-amber-200 p-5">
              <h2 className="mb-2 font-semibold">Reviewer view: hidden details from the report</h2>
              <p className="text-sm">{c.report_private_details || <span className="text-slate-500">The reporter added no private details.</span>}</p>
              <p className="mt-1 text-xs text-slate-500">Compare against the claimant's answers. Never share these details with the claimant.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {c.status === 'pending' && <button className="btn-secondary" onClick={() => act('review', { decision: 'start' }, 'Review started.')}>Start review</button>}
                {['pending', 'under_review'].includes(c.status) && <><button className="btn-success" onClick={() => setModal('approve')}>Approve</button><button className="btn-danger" onClick={() => setModal('reject')}>Reject</button></>}
              </div>
            </section>
          )}
          <section className="card p-5">
            <h2 className="mb-2 font-semibold">Evidence (private)</h2>
            {c.evidence.length === 0 ? <p className="text-sm text-slate-500">No evidence uploaded.</p> : <ul className="space-y-1">{c.evidence.map((e) => <li key={e.id}><button className="link inline-flex items-center gap-1 text-sm" onClick={() => download(e)}><Download className="h-3.5 w-3.5" /> {e.name}</button></li>)}</ul>}
            {c.can_add_evidence && <div className="mt-3"><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} aria-label="Upload evidence" /></div>}
          </section>
          {(c.handovers.length > 0 || c.can_schedule_handover || c.can_confirm_return) && (
            <section className="card p-5">
              <h2 className="mb-2 font-semibold">Handover</h2>
              {c.handovers.map((h) => (
                <div key={h.id} className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 p-3 text-sm">
                  <div><p className="font-medium">{h.reference} <StatusBadge status={h.status} /></p><p className="text-xs text-slate-500">{fmtDateTime(h.scheduled_for)} at {h.location}{h.confirmed_by ? ` - confirmed by ${h.confirmed_by}` : ''}</p></div>
                  {h.status === 'scheduled' && c.can_schedule_handover && <button className="btn-success btn-sm" onClick={() => confirmHandover(h.id)}>Confirm item handed over</button>}
                </div>
              ))}
              {c.can_schedule_handover && !scheduled && <button className="btn-primary" onClick={() => setModal('handover')}>Schedule handover</button>}
              {c.can_confirm_return && <button className="btn-success" onClick={() => setModal('return')}>Confirm I handed the item over</button>}
            </section>
          )}
          {c.dispute_status !== 'none' && <section className="card p-5 text-sm"><h2 className="mb-1 font-semibold">Dispute: {c.dispute_status}</h2><p>{c.dispute_note}</p>{c.dispute_resolution && <p className="mt-1 text-slate-600">Resolution: {c.dispute_resolution}</p>}</section>}
        </div>
        <aside className="space-y-4">
          <div className="card p-5"><h2 className="mb-3 font-semibold">Status timeline</h2><Timeline claim={c} /></div>
          <div className="card space-y-2 p-4">
            {c.can_withdraw && <button className="btn-secondary w-full" onClick={() => setModal('withdraw')}>Withdraw claim</button>}
            {c.can_dispute && <button className="btn-secondary w-full" onClick={() => setModal('dispute')}>Dispute decision</button>}
            <Link to={`/reports/${c.report.id}`} className="btn-ghost w-full">View item report</Link>
          </div>
        </aside>
      </div>

      <ConfirmDialog open={modal === 'approve'} title="Approve this claim?" confirmLabel="Approve" busy={busy} onClose={() => setModal(null)} onConfirm={() => act('review', { decision: 'approve', reason: text }, 'Claim approved.')}>
        <Field label="Note (optional)"><input className="input" value={text} onChange={(e) => setText(e.target.value)} /></Field>
        <p className="mt-2 text-xs text-slate-500">Only approve if the answers match the hidden details. The claimant is notified.</p>
      </ConfirmDialog>
      <ConfirmDialog open={modal === 'reject'} title="Reject this claim" confirmLabel="Reject" danger busy={busy} onClose={() => setModal(null)} onConfirm={() => act('review', { decision: 'reject', reason: text }, 'Claim rejected.')}>
        <Field label="Reason (required)"><textarea className="input" rows={3} value={text} onChange={(e) => setText(e.target.value)} /></Field>
      </ConfirmDialog>
      <ConfirmDialog open={modal === 'withdraw'} title="Withdraw your claim?" confirmLabel="Withdraw" danger busy={busy} onClose={() => setModal(null)} onConfirm={() => act('withdraw', {}, 'Claim withdrawn.')} />
      <ConfirmDialog open={modal === 'dispute'} title="Dispute this decision" confirmLabel="Send to administrators" busy={busy} onClose={() => setModal(null)} onConfirm={() => act('dispute', { note: text }, 'Dispute sent.')}>
        <Field label="Why should this be reviewed again?"><textarea className="input" rows={3} value={text} onChange={(e) => setText(e.target.value)} /></Field>
      </ConfirmDialog>
      <ConfirmDialog open={modal === 'return'} title="Confirm return" message="Confirm you physically handed this item to the claimant. This marks the item as returned." confirmLabel="Confirm return" busy={busy} onClose={() => setModal(null)} onConfirm={() => act('confirm-return', {}, 'Item marked as returned.')} />
      <Modal open={modal === 'handover'} title="Schedule handover" onClose={() => setModal(null)} footer={<><button className="btn-secondary" onClick={() => setModal(null)}>Cancel</button><button className="btn-primary" disabled={busy || !when || !where} onClick={doHandover}>Schedule</button></>}>
        <div className="space-y-3"><Field label="Date and time"><input type="datetime-local" className="input" value={when} onChange={(e) => setWhen(e.target.value)} /></Field><Field label="Location"><input className="input" value={where} onChange={(e) => setWhere(e.target.value)} placeholder="Security desk, Main Gate" /></Field></div>
      </Modal>
    </>
  );
}
