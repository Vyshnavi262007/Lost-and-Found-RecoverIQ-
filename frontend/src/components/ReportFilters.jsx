import { Search } from 'lucide-react';
import useFetch from '../hooks/useFetch.js';

export default function ReportFilters({ value, onChange, showStatus = true }) {
  const cats = useFetch('/categories/');
  const locs = useFetch('/locations/');
  const set = (k, v) => onChange({ ...value, [k]: v, page: 1 });
  return (
    <div className="card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="relative sm:col-span-2">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input className="input pl-9" placeholder="Search title or description" aria-label="Search" value={value.q || ''} onChange={(e) => set('q', e.target.value)} />
      </div>
      <select className="input" aria-label="Lost or found" value={value.type || ''} onChange={(e) => set('type', e.target.value)}>
        <option value="">Lost &amp; found</option><option value="lost">Lost</option><option value="found">Found</option>
      </select>
      <select className="input" aria-label="Category" value={value.category || ''} onChange={(e) => set('category', e.target.value)}>
        <option value="">All categories</option>{(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <select className="input" aria-label="Campus location" value={value.location || ''} onChange={(e) => set('location', e.target.value)}>
        <option value="">All locations</option>{(locs.data || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
      </select>
      {showStatus && (
        <select className="input" aria-label="Status" value={value.status || ''} onChange={(e) => set('status', e.target.value)}>
          <option value="">Any status</option><option value="open">Open</option><option value="claim_pending">Claim approved</option><option value="returned">Returned</option><option value="closed">Closed</option>
        </select>
      )}
      <input type="date" className="input" aria-label="From date" value={value.date_from || ''} onChange={(e) => set('date_from', e.target.value)} />
      <input type="date" className="input" aria-label="To date" value={value.date_to || ''} onChange={(e) => set('date_to', e.target.value)} />
      <select className="input" aria-label="Sort" value={value.ordering || 'newest'} onChange={(e) => set('ordering', e.target.value)}>
        <option value="newest">Newest first</option><option value="relevance">Most relevant</option>
      </select>
    </div>
  );
}
