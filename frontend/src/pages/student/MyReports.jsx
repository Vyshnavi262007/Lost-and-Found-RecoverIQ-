import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { errorMessage } from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import ReportCard from '../../components/ReportCard.jsx';
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner, Tabs } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';

export function MyReports() {
  const [tab, setTab] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/reports/mine/', { type: tab, page });
  return (
    <>
      <PageHeader title="My reports" actions={<Link to="/report/new" className="btn-primary">New report</Link>} />
      <Tabs tabs={[['', 'All'], ['lost', 'Lost'], ['found', 'Found']]} value={tab} onChange={(t) => { setTab(t); setPage(1); }} />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? (
        <EmptyState title="You have not reported anything yet" action={<Link to="/report/new?type=lost" className="btn-primary">Report a lost item</Link>} />
      ) : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.results.map((r) => <ReportCard key={r.id} report={r} />)}</div>}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}

export function Bookmarks() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch('/bookmarks/', { page });
  const remove = async (r) => { try { await api.delete(`/reports/${r.id}/bookmark/`); reload(); } catch (e) { toast.error(errorMessage(e)); } };
  return (
    <>
      <PageHeader title="Bookmarks" subtitle="Reports you saved." />
      {loading ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : data.results.length === 0 ? <EmptyState title="No bookmarks yet" hint="Use the bookmark icon on any report to save it here." /> :
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.results.map((r) => <ReportCard key={r.id} report={{ ...r, is_bookmarked: true }} onBookmark={remove} />)}</div>}
      <Pagination data={data} page={page} onPage={setPage} />
    </>
  );
}
