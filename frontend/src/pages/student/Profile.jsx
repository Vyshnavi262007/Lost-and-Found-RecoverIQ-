import { useState } from 'react';
import api, { errorMessage, fieldErrors } from '../../api/client.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { Field, PageHeader } from '../../components/ui.jsx';

export default function Profile() {
  const { user, setUser, adoptToken } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ first_name: user.first_name, last_name: user.last_name, student_id: user.student_id, department: user.department, year: user.year || '' });
  const [pw, setPw] = useState({ old_password: '', new_password: '' });
  const [errors, setErrors] = useState({});
  const [pwErrors, setPwErrors] = useState({});

  const save = async (e) => {
    e.preventDefault();
    try { const { data } = await api.patch('/auth/me/', { ...form, year: form.year ? Number(form.year) : null }); setUser(data); setErrors({}); toast.success('Profile saved.'); } catch (err) { setErrors(fieldErrors(err)); toast.error(errorMessage(err)); }
  };
  const change = async (e) => {
    e.preventDefault();
    try { const { data } = await api.post('/auth/change-password/', pw); adoptToken(data); setPw({ old_password: '', new_password: '' }); setPwErrors({}); toast.success('Password changed.'); } catch (err) { setPwErrors(fieldErrors(err)); toast.error('Could not change password.'); }
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  return (
    <>
      <PageHeader title="Profile & settings" subtitle={`${user.email} - ${user.role}${user.can_release_items ? ' (can release items)' : ''}`} />
      <div className="grid max-w-4xl gap-6 md:grid-cols-2">
        <form onSubmit={save} className="card space-y-4 p-5">
          <h2 className="font-semibold">Your details</h2>
          <div className="grid grid-cols-2 gap-3"><Field label="First name" error={errors.first_name}><input className="input" value={form.first_name} onChange={set('first_name')} /></Field><Field label="Last name"><input className="input" value={form.last_name} onChange={set('last_name')} /></Field></div>
          <Field label="Student ID"><input className="input" value={form.student_id} onChange={set('student_id')} /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Department"><input className="input" value={form.department} onChange={set('department')} /></Field><Field label="Year" error={errors.year}><input type="number" min="1" max="8" className="input" value={form.year} onChange={set('year')} /></Field></div>
          <p className="text-xs text-slate-500">Other users only ever see your first name and last initial.</p>
          <button className="btn-primary">Save profile</button>
        </form>
        <form onSubmit={change} className="card space-y-4 self-start p-5">
          <h2 className="font-semibold">Change password</h2>
          <Field label="Current password" error={pwErrors.old_password}><input type="password" autoComplete="current-password" className="input" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} /></Field>
          <Field label="New password" error={pwErrors.new_password || pwErrors.non_field_errors}><input type="password" autoComplete="new-password" className="input" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
          <button className="btn-primary">Change password</button>
        </form>
      </div>
    </>
  );
}
