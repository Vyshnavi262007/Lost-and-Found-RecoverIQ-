import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';

export default function Logo({ to = '/', light = false }) {
  return (
    <Link to={to} className="flex items-center gap-2" aria-label="RecoverIQ home">
      <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-navy-800">
        <Search className="h-4 w-4 text-white" strokeWidth={2.5} />
        <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-ok-600" />
      </span>
      <span className={`text-lg font-semibold tracking-tight ${light ? 'text-white' : 'text-navy-900'}`}>Recover<span className="text-navy-500">IQ</span></span>
    </Link>
  );
}
