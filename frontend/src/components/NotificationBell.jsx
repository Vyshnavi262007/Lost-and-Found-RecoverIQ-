import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell } from 'lucide-react';
import api from '../api/client.js';

export default function NotificationBell() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let alive = true;
    const load = () => api.get('/notifications/summary/').then((r) => alive && setCount(r.data.unread_count)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    window.addEventListener('riq:notifications', load);
    return () => { alive = false; clearInterval(t); window.removeEventListener('riq:notifications', load); };
  }, []);
  return (
    <Link to="/notifications" className="relative rounded-lg p-2 text-navy-700 hover:bg-navy-50" aria-label={`Notifications${count ? `, ${count} unread` : ''}`}>
      <Bell className="h-5 w-5" />
      {count > 0 && <span className="absolute right-0.5 top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">{count > 99 ? '99+' : count}</span>}
    </Link>
  );
}
