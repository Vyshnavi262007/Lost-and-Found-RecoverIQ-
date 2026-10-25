import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import api, { errorMessage, fieldErrors } from '../../api/client.js';
import { Field } from '../../components/ui.jsx';
import { useAuth, homeFor } from '../../context/AuthContext.jsx';

const Shell = ({ title, subtitle, children }) => (
  <div className="mx-auto max-w-md px-4 py-12">
    <div className="card p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </div>
  </div>
);

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [unverified, setUnverified] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(''); setUnverified(false);
    try {
      const user = await login(form.email, form.password);
      nav(params.get('next') || loc.state?.from || homeFor(user), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setUnverified(err.response?.data?.code === 'email_unverified');
    } finally { setBusy(false); }
  };

  return (
    <Shell title="Log in" subtitle="Use your college email address.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}{unverified && <> Check your inbox for the verification link.</>}</div>}
        <Field label="College email" htmlFor="email"><input id="email" type="email" autoComplete="username" className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></Field>
        <Field label="Password" htmlFor="password"><input id="password" type="password" autoComplete="current-password" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></Field>
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in...' : 'Log in'}</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-500">New here? <Link className="link" to="/register">Create an account</Link></p>
    </Shell>
  );
}

export function Register() {
  const [form, setForm] = useState({ full_name: '', email: '', student_id: '', department: '', year: '', password: '', account_type: 'student' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(''); setErrors({});
    try {
      const payload = { ...form, year: form.year ? Number(form.year) : null };
      const { data } = await api.post('/auth/register/', payload);
      setDone(data);
    } catch (err) {
      const f = fieldErrors(err);
      setErrors(f);
      if (!Object.keys(f).length) setError(errorMessage(err));
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <Shell title="Check your email">
        <p className="text-sm text-slate-600">Your account was created. Verify your college email to sign in{['staff', 'admin'].includes(form.account_type) ? `, then an administrator must approve your ${form.account_type} access. Until then you can use RecoverIQ as a regular member` : ''}.</p>
        {done.dev_verification_link ? (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
            <p className="font-medium text-amber-800">Development mode</p>
            <p className="mt-1 text-amber-700">No email was sent because SMTP is not configured. Use this local verification link:</p>
            <a className="link mt-2 block break-all" href={done.dev_verification_link.replace(/^https?:\/\/[^/]+/, '')}>{done.dev_verification_link}</a>
          </div>
        ) : <p className="mt-3 text-sm text-slate-500">We sent a verification link to {form.email}.</p>}
        <Link to="/login" className="btn-primary mt-5 w-full">Go to log in</Link>
      </Shell>
    );
  }

  return (
    <Shell title="Create your account" subtitle="Use your college or university email (for example .edu or .ac.in).">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div>}
        <Field label="I am a" error={errors.account_type} htmlFor="t" hint={['staff', 'admin'].includes(form.account_type) ? 'Needs administrator approval before you get any special powers.' : undefined}>
          <select id="t" className="input" value={form.account_type} onChange={set('account_type')}>
            <option value="student">Student</option><option value="faculty">Faculty / teaching staff</option><option value="staff">Campus staff (security, hostel, reception...)</option><option value="admin">Administrator</option>
          </select>
        </Field>
        <Field label="Full name" error={errors.full_name} htmlFor="n"><input id="n" className="input" value={form.full_name} onChange={set('full_name')} required /></Field>
        <Field label="College / university email" error={errors.email} htmlFor="e" hint="Any recognised academic address works, e.g. name@college.edu or name@university.ac.in. Verified by email link."><input id="e" type="email" className="input" value={form.email} onChange={set('email')} required /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={form.account_type === 'student' ? 'Student ID (optional)' : 'Employee ID (optional)'} error={errors.student_id} htmlFor="s"><input id="s" className="input" value={form.student_id} onChange={set('student_id')} /></Field>
          <Field label="Year (optional)" error={errors.year} htmlFor="y"><input id="y" type="number" min="1" max="8" className="input" value={form.year} onChange={set('year')} /></Field>
        </div>
        <Field label="Department (optional)" htmlFor="d"><input id="d" className="input" value={form.department} onChange={set('department')} /></Field>
        <Field label="Password" error={errors.password || errors.non_field_errors} hint="At least 8 characters; not a common or all-numeric password." htmlFor="p"><input id="p" type="password" autoComplete="new-password" className="input" value={form.password} onChange={set('password')} required /></Field>
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating...' : 'Create account'}</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-500">Already registered? <Link className="link" to="/login">Log in</Link></p>
    </Shell>
  );
}

export function VerifyEmail() {
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: 'working', message: '' });
  useEffect(() => {
    const token = params.get('token');
    if (!token) { setState({ status: 'info', message: 'Open the verification link from your email. An administrator can also verify accounts manually.' }); return; }
    api.post('/auth/verify-email/', { token })
      .then((r) => setState({ status: 'ok', message: r.data.detail }))
      .catch((e) => setState({ status: 'error', message: errorMessage(e) }));
  }, [params]);
  return (
    <Shell title="Email verification">
      <p className={`text-sm ${state.status === 'error' ? 'text-red-600' : state.status === 'ok' ? 'text-ok-700' : 'text-slate-600'}`}>{state.status === 'working' ? 'Verifying...' : state.message}</p>
      <Link to="/login" className="btn-primary mt-5 w-full">Go to log in</Link>
    </Shell>
  );
}
