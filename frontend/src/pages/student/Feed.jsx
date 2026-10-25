import { useSearchParams } from 'react-router-dom';
import api from '../../api/client.js';
import useFetch from '../../hooks/useFetch.js';
import ReportCard from '../../components/ReportCard.jsx';
import ReportFilters from '../../components/ReportFilters.jsx';
import { CardSkeletons, EmptyState, ErrorState, PageHeader, Pagination } from '../../components/ui.jsx';
import { useToast } from '../../context/ToastContext.jsx';
import { errorMessage } from '../../api/client.js';

export default function Feed() {
  const [sp, setSp] = useSearchParams();
  const toast = useToast();
  const filters = Object.fromEntries(sp.entries());
  const page = Number(filters.page || 1);
  const params = { ...filters, status: filters.status ?? 'open' };
  if (params.ordering === 'newest') delete params.ordering;
  const { data, loading, error, reload, setData } = useFetch('/reports/', params);

  const onFilters = (v) => {
    const next = {};
    Object.entries(v).forEach(([k, val]) => { if (val !== '' && val != null && !(k === 'page' && val === 1)) next[k] = val; });
    if (!('status' in v) || v.status === undefined) next.status = 'open';
    if (v.status === '') next.status = '';
    setSp(next);
  };
  const toggle = async (r) => {
    try {
      await (r.is_bookmarked ? api.delete(`/reports/${r.id}/bookmark/`) : api.post(`/reports/${r.id}/bookmark/`));
      setData({ ...data, results: data.results.map((x) => (x.id === r.id ? { ...x, is_bookmarked: !r.is_bookmarked } : x)) });
    } catch (e) { toast.error(errorMessage(e)); }
  };

  return (
    <>
      <PageHeader title="Community feed" subtitle="Lost and found reports from your campus." />
      <ReportFilters value={{ ...filters, status: filters.status ?? 'open' }} onChange={onFilters} />
      {loading ? <CardSkeletons /> : error ? <ErrorState message={error} onRetry={reload} /> :
        data.results.length === 0 ? <EmptyState title="No reports match your filters" hint="Try removing a filter or searching for different words." /> : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data.results.map((r) => <ReportCard key={r.id} report={r} onBookmark={toggle} />)}</div>
            <Pagination data={data} page={page} onPage={(p) => onFilters({ ...filters, status: filters.status ?? 'open', page: p })} />
          </>
        )}
    </>
  );
}
