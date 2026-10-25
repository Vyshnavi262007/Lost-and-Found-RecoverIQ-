import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import api, { errorMessage, fieldErrors } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import ImagePicker from '../../components/ImagePicker.jsx';
import { Field, PageHeader, Spinner, ErrorState } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { toFormData } from '../../utils/format.js';

const today = () => new Date().toISOString().slice(0, 10);
const BLANK = { type: 'lost', title: '', category: '', description: '', brand: '', color: '', features: '', location: '', building: '', date: today(), time: '', private_details: '', contact_preference: 'in_app', notes: '' };
const DRAFT_KEY = 'riq_report_draft';

export default function ReportForm({ edit = false }) {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const toast = useToast();
  const cats = useFetch('/categories/');
  const locs = useFetch('/locations/');
  const existing = useFetch(edit ? `/reports/${id}/` : null);
  const [form, setForm] = useState(() => {
    if (edit) return BLANK;
    const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
    const type = sp.get('type') === 'found' ? 'found' : 'lost';
    return draft && draft.type === type ? draft : { ...BLANK, type };
  });
  const [files, setFiles] = useState([]);
  const [removed, setRemoved] = useState([]);
  const [errors, setErrors] = useState({});
  const [progress, setProgress] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = sp.get('type');
    if (!edit && (t === 'lost' || t === 'found')) setForm((f) => (f.type === t ? f : { ...f, type: t }));
  }, [sp, edit]);
  useEffect(() => {
    const r = existing.data;
    if (edit && r) setForm({ type: r.type, title: r.title, category: r.category.id, description: r.description, brand: r.brand, color: r.color, features: r.features, location: r.location.id, building: r.building, date: r.date, time: r.time ? r.time.slice(0, 5) : '', private_details: r.private_details || '', contact_preference: r.contact_preference, notes: r.notes });
  }, [existing.data, edit]);
  useEffect(() => { if (!edit) localStorage.setItem(DRAFT_KEY, JSON.stringify(form)); }, [form, edit]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (form.title.trim().length < 3) e.title = 'Enter a title (at least 3 characters).';
    if (!form.category) e.category = 'Choose a category.';
    if (form.description.trim().length < 10) e.description = 'Describe the item in at least 10 characters.';
    if (!form.location) e.location = 'Choose a campus location.';
    if (!form.date || form.date > today()) e.date = 'Choose a valid date (not in the future).';
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const v = validate();
    setErrors(v);
    if (Object.keys(v).length) { toast.error('Please fix the highlighted fields.'); return; }
    setBusy(true); setProgress(0);
    try {
      const fd = toFormData(form, 'images', files);
      removed.forEach((rid) => fd.append('remove_image_ids', rid));
      const cfg = { onUploadProgress: (p) => p.total && setProgress(Math.round((p.loaded / p.total) * 100)) };
      const { data } = edit ? await api.patch(`/reports/${id}/`, fd, cfg) : await api.post('/reports/', fd, cfg);
      if (!edit) localStorage.removeItem(DRAFT_KEY);
      toast.success(edit ? 'Report updated.' : 'Report submitted. We are checking for possible matches.');
      nav(`/reports/${data.id}`);
    } catch (err) {
      const f = fieldErrors(err);
      setErrors(f);
      toast.error(Object.keys(f).length ? 'Some fields need attention.' : errorMessage(err));
    } finally { setBusy(false); setProgress(null); }
  };

  if (edit && existing.loading) return <Spinner />;
  if (edit && existing.error) return <ErrorState message={existing.error} onRetry={existing.reload} />;
  const lost = form.type === 'lost';
  const keptImages = (existing.data?.images || []).filter((i) => !removed.includes(i.id));

  return (
    <>
      <PageHeader title={edit ? 'Edit report' : lost ? 'Report a lost item' : 'Report a found item'} subtitle={lost ? 'The more detail you add, the better the matches.' : 'Thank you for helping. Add details only the real owner would know in the private box.'} />
      <form onSubmit={submit} className="card max-w-3xl space-y-5 p-5" noValidate>
        {!edit && (
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5" role="group" aria-label="Report type">
            {['lost', 'found'].map((t) => <button type="button" key={t} aria-pressed={form.type === t} onClick={() => setForm({ ...form, type: t })} className={`rounded-md px-4 py-1.5 text-sm font-medium ${form.type === t ? 'bg-navy-800 text-white' : 'text-slate-600'}`}>{t === 'lost' ? 'I lost something' : 'I found something'}</button>)}
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Item title" error={errors.title} htmlFor="title"><input id="title" className="input" value={form.title} onChange={set('title')} maxLength={160} placeholder="e.g. Black leather wallet" /></Field>
          <Field label="Category" error={errors.category} htmlFor="cat">
            <select id="cat" className="input" value={form.category} onChange={set('category')}><option value="">Select...</option>{(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
          </Field>
        </div>
        <Field label="Description" error={errors.description} htmlFor="desc"><textarea id="desc" rows={4} className="input" value={form.description} onChange={set('description')} placeholder="Size, condition, what it looks like..." /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Brand (optional)" htmlFor="brand"><input id="brand" className="input" value={form.brand} onChange={set('brand')} /></Field>
          <Field label="Colour (optional)" htmlFor="color"><input id="color" className="input" value={form.color} onChange={set('color')} /></Field>
        </div>
        <Field label="Distinguishing features (public)" htmlFor="feat"><textarea id="feat" rows={2} className="input" value={form.features} onChange={set('features')} placeholder="Stickers, scratches, engravings you are happy to show publicly" /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Campus location" error={errors.location} htmlFor="loc">
            <select id="loc" className="input" value={form.location} onChange={set('location')}><option value="">Select...</option>{(locs.data || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select>
          </Field>
          <Field label="Building / block / room (optional)" htmlFor="bld"><input id="bld" className="input" value={form.building} onChange={set('building')} /></Field>
          <Field label={lost ? 'Date lost' : 'Date found'} error={errors.date} htmlFor="date"><input id="date" type="date" max={today()} className="input" value={form.date} onChange={set('date')} /></Field>
          <Field label="Approximate time (optional)" error={errors.time} htmlFor="time"><input id="time" type="time" className="input" value={form.time} onChange={set('time')} /></Field>
        </div>
        <Field label="Photos" error={errors.images}><ImagePicker files={files} onChange={setFiles} onProblem={toast.error} existing={keptImages} onRemoveExisting={(rid) => setRemoved([...removed, rid])} /></Field>
        <Field label="Private identifying details" error={errors.private_details} hint="Never shown publicly. Only reviewers who verify a claim can read this (e.g. contents, serial number, marks).">
          <textarea rows={3} className="input" value={form.private_details} onChange={set('private_details')} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Contact preference" htmlFor="cp"><select id="cp" className="input" value={form.contact_preference} onChange={set('contact_preference')}><option value="in_app">In-app messages</option><option value="staff_desk">Via campus desk</option></select></Field>
          <Field label="Additional notes (optional)" htmlFor="notes"><input id="notes" className="input" value={form.notes} onChange={set('notes')} /></Field>
        </div>
        {progress !== null && <div className="h-2 overflow-hidden rounded bg-slate-100" role="progressbar" aria-valuenow={progress}><div className="h-full bg-navy-600 transition-all" style={{ width: `${progress}%` }} /></div>}
        <div className="flex gap-2">
          <button className="btn-primary" disabled={busy}>{busy ? 'Saving...' : edit ? 'Save changes' : 'Submit report'}</button>
          <button type="button" className="btn-secondary" onClick={() => nav(-1)}>Cancel</button>
        </div>
        {!edit && <p className="text-xs text-slate-400">Your progress is saved on this device as a draft until you submit.</p>}
      </form>
    </>
  );
}
