import { useState } from 'react';
import api, { errorMessage, fieldErrors } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { ConfirmDialog, Modal } from '../../components/Modal.jsx';
import { EmptyState, ErrorState, Field, PageHeader, Pagination, Spinner, StatusBadge } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { useAuth } from '../../context/AuthContext.jsx';

export function Users() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ q: '', role: '', active: '', page: 1 });
  const { data, loading, error, reload } = useFetch('/admin/users/', f);
  const [target, setTarget] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'staff', staff_title: '', can_review_claims: true, can_release_items: false });
  const [errs, setErrs] = useState({});
  const patch = async (u, body, ok) => { try { await api.patch(`/admin/users/${u.id}/`, body); toast.success(ok); setTarget(null); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  const create = async () => { try { await api.post('/admin/users/', form); toast.success('Account created.'); setCreating(false); reload(); } catch (e) { setErrs(fieldErrors(e)); toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title="User management" actions={<button className="btn-primary" onClick={() => setCreating(true)}>Create account</button>} />
      <div className="card mb-4 flex flex-wrap gap-3 p-3">
        <input className="input max-w-xs" placeholder="Search name, email, ID" aria-label="Search users" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value, page: 1 })} />
        <select className="input max-w-[10rem]" aria-label="Role" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value, page: 1 })}><option value="">All roles</option><option value="student">Students</option><option value="faculty">Faculty</option><option value="staff">Staff</option><option value="admin">Admins</option></select>
        <select className="input max-w-[10rem]" aria-label="Active" value={f.active} onChange={(e) => setF({ ...f, active: e.target.value, page: 1 })}><option value="">Any state</option><option value="1">Active</option><option value="0">Deactivated</option></select>
      </div>
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No users found" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr><th className="th">Name</th><th className="th">Role</th><th className="th">Verified</th><th className="th">State</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.results.map((u) => (
            <tr key={u.id}><td className="td">{u.full_name}<span className="block text-xs text-slate-500">{u.email}</span></td>
              <td className="td capitalize">{u.role}{u.role === 'staff' && <span className="block text-xs text-slate-500">{[u.can_review_claims && 'review', u.can_release_items && 'release'].filter(Boolean).join(', ') || 'no claim powers'}</span>}</td>
              <td className="td">{u.email_verified ? 'Yes' : <button className="link" onClick={() => patch(u, { email_verified: true }, 'Marked as verified.')}>Verify manually</button>}</td>
              <td className="td"><StatusBadge status={u.is_active ? 'open' : 'closed'} label={u.is_active ? 'Active' : 'Deactivated'} /></td>
              <td className="td text-right"><button className="btn-secondary btn-sm" onClick={() => setTarget(u)} disabled={u.id === me.id}>Manage</button></td></tr>))}</tbody></table></div>
      )}
      <Pagination data={data} page={f.page} onPage={(p) => setF({ ...f, page: p })} />
      <Modal open={!!target} title={target ? `Manage ${target.full_name}` : ''} onClose={() => setTarget(null)}>
        {target && <div className="space-y-3">
          <Field label="Role"><select className="input" value={target.role} onChange={(e) => setTarget({ ...target, role: e.target.value })}><option value="student">Student</option><option value="faculty">Faculty</option><option value="staff">Campus staff</option><option value="admin">Administrator</option></select></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={target.can_review_claims} onChange={(e) => setTarget({ ...target, can_review_claims: e.target.checked })} /> Can review claims</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={target.can_release_items} onChange={(e) => setTarget({ ...target, can_release_items: e.target.checked })} /> Can release items held by the college</label>
          <div className="flex flex-wrap justify-between gap-2 pt-2">
            <button className={target.is_active ? 'btn-danger' : 'btn-success'} onClick={() => patch(target, { is_active: !target.is_active }, target.is_active ? 'Account deactivated.' : 'Account activated.')}>{target.is_active ? 'Deactivate account' : 'Activate account'}</button>
            <button className="btn-primary" onClick={() => patch(target, { role: target.role, can_review_claims: target.can_review_claims, can_release_items: target.can_release_items }, 'User updated.')}>Save changes</button>
          </div></div>}
      </Modal>
      <Modal open={creating} title="Create account" onClose={() => setCreating(false)} footer={<><button className="btn-secondary" onClick={() => setCreating(false)}>Cancel</button><button className="btn-primary" onClick={create}>Create</button></>}>
        <div className="space-y-3">
          <Field label="Full name" error={errs.full_name}><input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <Field label="Email (allowed college domain)" error={errs.email}><input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="Temporary password" error={errs.password}><input type="password" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Role"><select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="staff">Staff</option><option value="faculty">Faculty</option><option value="student">Student</option><option value="admin">Admin</option></select></Field><Field label="Job title"><input className="input" value={form.staff_title} onChange={(e) => setForm({ ...form, staff_title: e.target.value })} placeholder="Security" /></Field></div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.can_review_claims} onChange={(e) => setForm({ ...form, can_review_claims: e.target.checked })} /> Can review claims</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.can_release_items} onChange={(e) => setForm({ ...form, can_release_items: e.target.checked })} /> Can release items</label>
        </div>
      </Modal>
    </>
  );
}

export function StaffApprovals() {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch('/admin/staff-requests/');
  const [release, setRelease] = useState({});
  const [confirm, setConfirm] = useState(null);
  const decide = async (u, decision) => { try { await api.post(`/admin/staff-requests/${u.id}/`, { decision, can_review_claims: true, can_release_items: !!release[u.id] }); toast.success(decision === 'approve' ? 'Staff access approved.' : 'Request declined.'); setConfirm(null); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Staff approval queue" subtitle="Verified users who asked for staff access." />
      {data.length === 0 ? <EmptyState title="No pending requests" hint="Requests appear after the user verifies their email." /> : (
        <ul className="card divide-y divide-slate-100">{data.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"><div><p className="text-sm font-medium">{u.full_name}</p><p className="text-xs text-slate-500">{u.email} - requests <b>{u.requested_role || 'staff'}</b> access</p></div>
            <div className="flex flex-wrap items-center gap-3"><label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={!!release[u.id]} onChange={(e) => setRelease({ ...release, [u.id]: e.target.checked })} /> May release items</label>
              <button className="btn-success btn-sm" onClick={() => setConfirm(u)}>Approve</button><button className="btn-secondary btn-sm" onClick={() => decide(u, 'reject')}>Decline</button></div></li>))}</ul>
      )}
      <ConfirmDialog open={!!confirm} title="Grant elevated access?" message={confirm && `${confirm.full_name} will become ${confirm.requested_role || 'staff'} and will be able to review claims${release[confirm.id] ? ' and release items held by the college' : ''}. Only approve people you can verify.`} confirmLabel="Approve" onClose={() => setConfirm(null)} onConfirm={() => decide(confirm, 'approve')} />
    </>
  );
}
