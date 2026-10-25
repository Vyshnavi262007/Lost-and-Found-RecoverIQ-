import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api, { errorMessage, fieldErrors } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import ImagePicker from '../../components/ImagePicker.jsx';
import { EmptyState, ErrorState, Field, PageHeader, Pagination, Spinner, StatusBadge } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { fmtDate, fmtDateTime, toFormData } from '../../utils/format.js';

export function Inventory() {
  const [f, setF] = useState({ q: '', status: '', page: 1 });
  const { data, loading, error, reload } = useFetch('/inventory/', f);
  return (
    <>
      <PageHeader title="Lost-property inventory" actions={<Link to="/staff/inventory/new" className="btn-primary">Add inventory item</Link>} />
      <div className="card mb-4 flex flex-wrap gap-3 p-3">
        <input className="input max-w-xs" placeholder="Search name, reference, storage" aria-label="Search inventory" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} />
        <select className="input max-w-[12rem]" aria-label="Status" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value, page: 1 })}><option value="">Any status</option><option value="stored">In storage</option><option value="returned">Returned</option><option value="disposed">Disposed</option></select>
      </div>
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No inventory records" hint="Record physical items handed in to the desk." /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr><th className="th">Reference</th><th className="th">Item</th><th className="th">Storage</th><th className="th">Received</th><th className="th">Status</th><th className="th">Claims</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.results.map((i) => (
            <tr key={i.id} className="hover:bg-slate-50"><td className="td"><Link className="link" to={`/staff/inventory/${i.id}`}>{i.reference}</Link></td><td className="td">{i.name}<span className="block text-xs text-slate-500">{i.category}</span></td><td className="td">{i.storage_location}</td><td className="td">{fmtDate(i.received_at)} by {i.received_by}</td><td className="td"><StatusBadge status={i.status} /></td><td className="td">{i.claim_count}</td></tr>))}</tbody></table></div>
      )}
      <Pagination data={data} page={f.page} onPage={(p) => setF({ ...f, page: p })} />
    </>
  );
}

export function InventoryForm() {
  const nav = useNavigate();
  const toast = useToast();
  const cats = useFetch('/categories/');
  const locs = useFetch('/locations/');
  const [form, setForm] = useState({ title: '', category: '', description: '', color: '', brand: '', location: '', date: new Date().toISOString().slice(0, 10), private_details: '', storage_location: '', condition_notes: '' });
  const [files, setFiles] = useState([]);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try { const { data } = await api.post('/inventory/', toFormData(form, 'images', files)); toast.success(`Recorded as ${data.reference}.`); nav(`/staff/inventory/${data.id}`); }
    catch (err) { setErrors(fieldErrors(err)); toast.error(errorMessage(err)); } finally { setBusy(false); }
  };
  return (
    <>
      <PageHeader title="Add inventory item" subtitle="Creates a found-item report and a lost-property record, and runs matching." />
      <form onSubmit={submit} className="card max-w-3xl space-y-4 p-5" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Item name" error={errors.title}><input className="input" value={form.title} onChange={set('title')} /></Field>
          <Field label="Category" error={errors.category}><select className="input" value={form.category} onChange={set('category')}><option value="">Select...</option>{(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        </div>
        <Field label="Public description" error={errors.description}><textarea className="input" rows={3} value={form.description} onChange={set('description')} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Colour"><input className="input" value={form.color} onChange={set('color')} /></Field>
          <Field label="Brand"><input className="input" value={form.brand} onChange={set('brand')} /></Field>
          <Field label="Where it was found" error={errors.location}><select className="input" value={form.location} onChange={set('location')}><option value="">Select...</option>{(locs.data || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></Field>
          <Field label="Date found" error={errors.date}><input type="date" className="input" value={form.date} onChange={set('date')} /></Field>
          <Field label="Storage location" error={errors.storage_location}><input className="input" value={form.storage_location} onChange={set('storage_location')} placeholder="Locker 3, security desk" /></Field>
          <Field label="Condition notes"><input className="input" value={form.condition_notes} onChange={set('condition_notes')} /></Field>
        </div>
        <Field label="Private identifying details" hint="Used only to verify claims. Never shown publicly."><textarea className="input" rows={2} value={form.private_details} onChange={set('private_details')} /></Field>
        <Field label="Photos" error={errors.images}><ImagePicker files={files} onChange={setFiles} onProblem={toast.error} /></Field>
        <button className="btn-primary" disabled={busy}>{busy ? 'Saving...' : 'Add to inventory'}</button>
      </form>
    </>
  );
}

export function InventoryDetail() {
  const { id } = useParams();
  const toast = useToast();
  const { data: i, loading, error, reload } = useFetch(`/inventory/${id}/`);
  const [loc, setLoc] = useState(null);
  if (loading && !i) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const save = async () => { try { await api.patch(`/inventory/${id}/`, { storage_location: loc }); toast.success('Storage location updated.'); setLoc(null); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title={i.name} subtitle={`${i.reference} - received ${fmtDateTime(i.received_at)} by ${i.received_by}`} actions={<StatusBadge status={i.status} />} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="card p-5 text-sm">
            {i.thumbnail && <img src={i.thumbnail} alt={i.name} className="mb-3 h-40 rounded-lg object-cover" />}
            <p>{i.report_description}</p>
            <p className="mt-3"><span className="text-xs text-slate-500">Condition: </span>{i.condition_notes || '-'}</p>
            <p className="mt-2 rounded bg-amber-50 p-2"><b>Private details:</b> {i.report_private_details || 'none recorded'}</p>
            {i.report_id && <Link to={`/reports/${i.report_id}`} className="link mt-2 inline-block">Open linked report</Link>}
          </section>
          <section className="card p-5"><h2 className="mb-2 font-semibold">Related claims</h2>
            {i.claims.length === 0 ? <p className="text-sm text-slate-500">No claims.</p> : <ul className="divide-y divide-slate-100">{i.claims.map((c) => <li key={c.id}><Link to={`/claims/${c.id}`} className="flex items-center justify-between py-2 text-sm hover:underline"><span>#{c.id} {c.claimant_name}</span><StatusBadge status={c.status} /></Link></li>)}</ul>}</section>
          <section className="card p-5"><h2 className="mb-2 font-semibold">Handover history</h2>
            {i.handovers.length === 0 ? <p className="text-sm text-slate-500">No handovers yet.</p> : <ul className="space-y-2 text-sm">{i.handovers.map((h) => <li key={h.id}><b>{h.reference}</b> <StatusBadge status={h.status} /> <span className="text-slate-500">{fmtDateTime(h.scheduled_for)} at {h.location}{h.confirmed_by ? ` - confirmed by ${h.confirmed_by}` : ''}</span></li>)}</ul>}</section>
        </div>
        <aside className="card self-start p-5"><h2 className="mb-2 font-semibold">Storage location</h2>
          {loc === null ? <><p className="text-sm">{i.storage_location}</p>{i.status === 'stored' && <button className="btn-secondary btn-sm mt-3" onClick={() => setLoc(i.storage_location)}>Update</button>}</> :
            <div className="space-y-2"><input className="input" value={loc} onChange={(e) => setLoc(e.target.value)} aria-label="Storage location" /><div className="flex gap-2"><button className="btn-primary btn-sm" onClick={save}>Save</button><button className="btn-secondary btn-sm" onClick={() => setLoc(null)}>Cancel</button></div></div>}
          <p className="mt-4 text-xs text-slate-500">To release the item, approve a claim, then schedule and confirm the handover from the claim page.</p>
        </aside>
      </div>
    </>
  );
}
