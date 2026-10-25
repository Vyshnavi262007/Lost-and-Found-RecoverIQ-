import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import useFetch from '../../hooks/useFetch.js';
import { ErrorState, PageHeader, Spinner, Stat } from '../../components/ui.jsx';

const Chart = ({ title, empty, children }) => (
  <section className="card p-4"><h2 className="mb-3 text-sm font-semibold">{title}</h2>{empty ? <p className="py-10 text-center text-sm text-slate-500">No data for this period.</p> : <div className="h-64">{children}</div>}</section>
);

export default function Analytics() {
  const [days, setDays] = useState(30);
  const { data, loading, error, reload } = useFetch('/admin/analytics/', { days });
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const t = data.totals;
  const pct = (v) => (v == null ? 'n/a' : `${Math.round(v * 1000) / 10}%`);
  return (
    <>
      <PageHeader title="Recovery analytics" actions={<select className="input" aria-label="Time range" value={days} onChange={(e) => setDays(Number(e.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option><option value={0}>All time</option></select>} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Registered users" value={t.users} hint={`${t.active_students} students, ${t.active_staff} staff`} />
        <Stat label="Lost reports" value={t.lost_reports} />
        <Stat label="Found reports" value={t.found_reports} />
        <Stat label="Open reports" value={t.open_reports} />
        <Stat label="Possible matches" value={t.possible_matches} />
        <Stat label="Pending claims" value={t.pending_claims} />
        <Stat label="Items returned" value={t.items_returned} tone="ok" />
        <Stat label="Recovery rate" value={pct(t.recovery_rate)} hint={t.avg_hours_to_recovery == null ? 'Avg. time: n/a' : `Avg. ${t.avg_hours_to_recovery} h to recovery`} tone="ok" />
      </div>
      <p className="mt-2 text-xs text-slate-500">{data.definitions.recovery_rate}</p>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Chart title="Reports per day" empty={data.reports_by_day.length === 0}>
          <ResponsiveContainer><LineChart data={data.reports_by_day}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" fontSize={11} /><YAxis allowDecimals={false} fontSize={11} /><Tooltip /><Legend /><Line type="monotone" dataKey="lost" stroke="#35537f" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="found" stroke="#1f8a54" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
        </Chart>
        <Chart title="Most reported categories" empty={data.top_categories.length === 0}>
          <ResponsiveContainer><BarChart data={data.top_categories} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis type="number" allowDecimals={false} fontSize={11} /><YAxis type="category" dataKey="name" width={120} fontSize={11} /><Tooltip /><Bar dataKey="count" fill="#4a6a9b" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer>
        </Chart>
        <Chart title="Locations with most reports" empty={data.top_locations.length === 0}>
          <ResponsiveContainer><BarChart data={data.top_locations} layout="vertical" margin={{ left: 30 }}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis type="number" allowDecimals={false} fontSize={11} /><YAxis type="category" dataKey="name" width={120} fontSize={11} /><Tooltip /><Bar dataKey="count" fill="#1b3157" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer>
        </Chart>
      </div>
    </>
  );
}
