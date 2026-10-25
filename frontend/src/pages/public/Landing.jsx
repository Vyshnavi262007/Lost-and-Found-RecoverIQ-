import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, Camera, Handshake, Search, ShieldCheck, Sparkles, UserCheck, Lock } from 'lucide-react';
import useFetch from '../../hooks/useFetch.js';
import ReportCard from '../../components/ReportCard.jsx';
import { CardSkeletons, EmptyState, ErrorState } from '../../components/ui.jsx';
import { useAuth } from '../../context/AuthContext.jsx';

const STEPS = [
  { icon: Camera, title: 'Report it', text: 'Describe what you lost or found, add photos, and pick the campus location.' },
  { icon: Sparkles, title: 'We compare', text: 'RecoverIQ compares category, description, place and date to suggest possible matches. It is an estimate, not a guarantee.' },
  { icon: Bell, title: 'Get notified', text: 'You are alerted in the app when a strong possible match appears.' },
  { icon: Handshake, title: 'Verify and recover', text: 'Prove ownership, then collect your item from the finder or the campus lost-property desk.' },
];

export default function Landing() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const recent = useFetch('/public/recent/');
  const go = (e) => { e.preventDefault(); nav(user ? `/feed?q=${encodeURIComponent(q)}` : `/login?next=${encodeURIComponent('/feed?q=' + q)}`); };
  const report = (type) => nav(user ? `/report/new?type=${type}` : `/login?next=${encodeURIComponent('/report/new?type=' + type)}`);

  return (
    <>
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-14 text-center">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Lost Something? Let's Bring It Back.</h1>
          <p className="mx-auto mt-3 max-w-xl text-slate-600">RecoverIQ is the lost-and-found platform for your campus. Verified students and campus staff report items, match them, and return them safely.</p>
          <form onSubmit={go} className="mx-auto mt-6 flex max-w-xl gap-2" role="search">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input className="input pl-9" placeholder="Search for a wallet, ID card, keys..." aria-label="Search campus items" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <button className="btn-primary">Search</button>
          </form>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <button className="btn-secondary" onClick={() => report('lost')}>Report Lost Item</button>
            <button className="btn-secondary" onClick={() => report('found')}>Report Found Item</button>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="mb-5 flex items-end justify-between">
          <h2 className="text-xl font-semibold">Recently reported</h2>
          <Link to={user ? '/feed' : '/login'} className="link text-sm">See all reports</Link>
        </div>
        {recent.loading ? <CardSkeletons count={3} /> : recent.error ? <ErrorState message={recent.error} onRetry={recent.reload} /> :
          recent.data.length === 0 ? <EmptyState title="No public reports yet" hint="Be the first to report a lost or found item on your campus." /> :
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{recent.data.slice(0, 6).map((r) => <ReportCard key={r.id} report={r} to={user ? `/reports/${r.id}` : '/login'} />)}</div>}
        <p className="mt-3 text-xs text-slate-500">Public cards never show contact details or private identifying information.</p>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <h2 className="mb-6 text-xl font-semibold">How it works</h2>
          <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy-50 text-navy-700"><s.icon className="h-4 w-4" /></span>
                <div><h3 className="font-medium">{i + 1}. {s.title}</h3><p className="mt-1 text-sm text-slate-600">{s.text}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <h2 className="mb-6 text-xl font-semibold">Campus safety and verification</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            [UserCheck, 'College accounts only', 'Registration is limited to approved college email domains, and an email must be verified before sign-in.'],
            [Lock, 'Private details stay private', 'Identifying details you add to a report are hidden from the public and are only seen by reviewers who verify a claim.'],
            [ShieldCheck, 'Ownership is verified', 'Items are released only after an authorised reviewer approves a claim. A similarity score never releases an item.'],
          ].map(([Icon, t, d]) => (
            <div key={t} className="card p-5"><Icon className="mb-2 h-5 w-5 text-ok-600" /><h3 className="font-medium">{t}</h3><p className="mt-1 text-sm text-slate-600">{d}</p></div>
          ))}
        </div>
      </section>
    </>
  );
}
