import { Link } from 'react-router-dom';
import { Bookmark, MapPin, MessageSquare, Calendar, ImageOff } from 'lucide-react';
import { StatusBadge, TypeBadge } from './ui.jsx';
import { fmtDate } from '../utils/format.js';

export default function ReportCard({ report, onBookmark, to }) {
  const r = report;
  return (
    <article className="card flex flex-col overflow-hidden">
      <Link to={to || `/reports/${r.id}`} className="block">
        {r.thumbnail ? (
          <img src={r.thumbnail} alt={r.title} loading="lazy" className="h-36 w-full object-cover" />
        ) : (
          <div className="flex h-36 w-full items-center justify-center bg-navy-50 text-navy-300" aria-label="No photo"><ImageOff className="h-8 w-8" /></div>
        )}
      </Link>
      <div className="flex flex-1 flex-col p-4">
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <TypeBadge type={r.type} />
          <StatusBadge status={r.status} />
          <span className="text-xs text-slate-500">{r.category.name}</span>
        </div>
        <Link to={to || `/reports/${r.id}`} className="font-medium text-navy-900 hover:underline">{r.title}</Link>
        <p className="mt-1 line-clamp-2 text-sm text-slate-600">{r.short_description}</p>
        <dl className="mt-3 space-y-1 text-xs text-slate-500">
          <div className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" /> {r.location.name}</div>
          <div className="flex items-center gap-1.5"><Calendar className="h-3.5 w-3.5" /> {fmtDate(r.date)} &middot; posted {fmtDate(r.created_at)}</div>
        </dl>
        <div className="mt-auto flex items-center justify-between pt-4">
          <span className="text-xs text-slate-500">by {r.reporter_name}</span>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1" title="Comments"><MessageSquare className="h-3.5 w-3.5" /> {r.comment_count}</span>
            {onBookmark && (
              <button onClick={() => onBookmark(r)} aria-label={r.is_bookmarked ? 'Remove bookmark' : 'Bookmark'} aria-pressed={r.is_bookmarked}>
                <Bookmark className={`h-4 w-4 ${r.is_bookmarked ? 'fill-navy-700 text-navy-700' : 'text-slate-400 hover:text-navy-600'}`} />
              </button>
            )}
            <Link to={to || `/reports/${r.id}`} className="link">View details</Link>
          </div>
        </div>
      </div>
    </article>
  );
}
