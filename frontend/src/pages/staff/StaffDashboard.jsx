import { Link } from 'react-router-dom';
import useFetch from '../../hooks/useFetch.js';
import { ErrorState, PageHeader, Spinner, Stat } from '../../components/ui.jsx';

export default function StaffDashboard() {
  const { data, loading, error, reload } = useFetch('/dashboard/staff/');
  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Lost-property desk" subtitle={data.can_release_items ? 'You are authorised to release items.' : 'You can review claims but cannot release items held by the college.'}
        actions={<Link to="/staff/inventory/new" className="btn-primary">Add inventory item</Link>} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Link to="/staff/inventory"><Stat label="Items in storage" value={data.items_in_storage} /></Link>
        <Link to="/staff/claims"><Stat label="Claims to review" value={data.claims_to_review} /></Link>
        <Stat label="Approved, awaiting handover" value={data.approved_awaiting_handover} />
        <Link to="/staff/handovers"><Stat label="Scheduled handovers" value={data.scheduled_handovers} /></Link>
        <Stat label="Returned (30 days)" value={data.returned_last_30_days} tone="ok" />
      </div>
    </>
  );
}
