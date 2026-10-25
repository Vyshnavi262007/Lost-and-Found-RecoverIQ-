import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import { ClaimRow } from '../student/Claims.jsx';
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner, StatusBadge, Tabs } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { fmtDateTime } from '../../utils/format.js';

export function ClaimsReview() {
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/claims/', { scope: 'review', status, page });
  return (
    <>
      <PageHeader title="Claims review" subtitle="Claims you are authorised to review." />
      <Tabs tabs={[['pending', 'Pending'], ['under_review', 'Under review'], ['approved', 'Approved'], ['completed', 'Completed'], ['rejected', 'Rejected'], ['', 'All']]} value={status} onChange={(s) => { setStatus(s); setPage(1); }} />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No claims in this view" /> : <ul className="card divide-y divide-slate-100">{data.results.map((c) => <ClaimRow key={c.id} c={c} />)}</ul>}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}

export function Handovers() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/handovers/', { status, page });
  const act = async (h, what) => { try { await api.post(`/handovers/${h.id}/${what}/`); toast.success(what === 'confirm' ? 'Handover confirmed.' : 'Handover cancelled.'); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title="Handover history" />
      <Tabs tabs={[['', 'All'], ['scheduled', 'Scheduled'], ['completed', 'Completed'], ['cancelled', 'Cancelled']]} value={status} onChange={(s) => { setStatus(s); setPage(1); }} />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No handovers" /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead className="border-b border-slate-200"><tr><th className="th">Reference</th><th className="th">Item</th><th className="th">When / where</th><th className="th">Status</th><th className="th">Confirmed by</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.results.map((h) => (
            <tr key={h.id}><td className="td"><Link className="link" to={`/claims/${h.claim_id}`}>{h.reference}</Link></td><td className="td">{h.item}</td><td className="td">{fmtDateTime(h.scheduled_for)}<span className="block text-xs text-slate-500">{h.location}</span></td><td className="td"><StatusBadge status={h.status} /></td><td className="td">{h.confirmed_by || '-'}</td>
              <td className="td text-right">{h.status === 'scheduled' && <><button className="btn-success btn-sm mr-2" onClick={() => act(h, 'confirm')}>Confirm</button><button className="btn-ghost btn-sm" onClick={() => act(h, 'cancel')}>Cancel</button></>}</td></tr>))}</tbody></table></div>
      )}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}
