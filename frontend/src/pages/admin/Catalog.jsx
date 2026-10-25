import { useState } from 'react';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { ConfirmDialog, Modal } from '../../components/Modal.jsx';
import { EmptyState, ErrorState, Field, PageHeader, Spinner, StatusBadge } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';

function Manager({ title, url, columns, blank, fields, valid }) {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(url);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  const save = async () => {
    try { edit.id ? await api.patch(`${url}${edit.id}/`, edit) : await api.post(url, edit); toast.success('Saved.'); setEdit(null); reload(); } catch (e) { toast.error(errorMessage(e)); }
  };
  const remove = async () => { try { await api.delete(`${url}${del.id}/`); toast.success('Deleted.'); setDel(null); reload(); } catch (e) { toast.error(errorMessage(e)); setDel(null); } };
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title={title} actions={<button className="btn-primary" onClick={() => setEdit(blank)}>Add</button>} />
      {data.length === 0 ? <EmptyState title="Nothing yet" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr>{columns.map(([l]) => <th key={l} className="th">{l}</th>)}<th className="th">State</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.map((row) => (
            <tr key={row.id}>{columns.map(([l, k]) => <td key={l} className="td">{row[k] ?? '-'}</td>)}<td className="td"><StatusBadge status={row.is_active ? 'open' : 'closed'} label={row.is_active ? 'Active' : 'Inactive'} /></td>
              <td className="td text-right"><button className="btn-secondary btn-sm mr-2" onClick={() => setEdit(row)}>Edit</button><button className="btn-ghost btn-sm text-red-600" onClick={() => setDel(row)}>Delete</button></td></tr>))}</tbody></table></div>
      )}
      <Modal open={!!edit} title={edit?.id ? `Edit ${title.toLowerCase()}` : `Add to ${title.toLowerCase()}`} onClose={() => setEdit(null)} footer={<><button className="btn-secondary" onClick={() => setEdit(null)}>Cancel</button><button className="btn-primary" onClick={save} disabled={edit && !valid(edit)}>Save</button></>}>
        {edit && <div className="space-y-3">{fields(edit, (patch) => setEdit({ ...edit, ...patch }))}<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /> Active (selectable in forms)</label></div>}
      </Modal>
      <ConfirmDialog open={!!del} danger title="Delete?" message="Items already used by reports cannot be deleted. Deactivate them instead." confirmLabel="Delete" onClose={() => setDel(null)} onConfirm={remove} />
    </>
  );
}

export function Categories() {
  return <Manager title="Item categories" url="/admin/categories/" blank={{ name: '', group: 'other', is_active: true }} columns={[['Name', 'name'], ['Group', 'group']]} valid={(e) => e.name.trim()}
    fields={(e, set) => (<><Field label="Name"><input className="input" value={e.name} onChange={(x) => set({ name: x.target.value })} /></Field>
      <Field label="Group" hint="Categories in the same group get partial credit in matching."><select className="input" value={e.group} onChange={(x) => set({ group: x.target.value })}><option value="documents">Documents &amp; cards</option><option value="electronics">Electronics</option><option value="personal">Personal items</option><option value="study">Study materials</option><option value="other">Other</option></select></Field></>)} />;
}

export function Locations() {
  const campuses = useFetch('/campuses/');
  const first = campuses.data?.[0]?.id ?? '';
  return <Manager key={first} title="Campus locations" url="/admin/locations/" blank={{ campus: first, name: '', block: '', x_m: '', y_m: '', is_active: true }} columns={[['Name', 'name'], ['Block', 'block'], ['X (m)', 'x_m'], ['Y (m)', 'y_m']]} valid={(e) => e.name.trim() && e.campus}
    fields={(e, set) => (<><Field label="Name"><input className="input" value={e.name} onChange={(x) => set({ name: x.target.value })} /></Field>
      <Field label="Campus"><select className="input" value={e.campus} onChange={(x) => set({ campus: Number(x.target.value) })}>{(campuses.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
      <Field label="Block / zone"><input className="input" value={e.block} onChange={(x) => set({ block: x.target.value })} /></Field>
      <div className="grid grid-cols-2 gap-3"><Field label="X (metres)" hint="Campus-grid coordinates used for proximity"><input type="number" className="input" value={e.x_m ?? ''} onChange={(x) => set({ x_m: x.target.value === '' ? null : Number(x.target.value) })} /></Field><Field label="Y (metres)"><input type="number" className="input" value={e.y_m ?? ''} onChange={(x) => set({ y_m: x.target.value === '' ? null : Number(x.target.value) })} /></Field></div></>)} />;
}
