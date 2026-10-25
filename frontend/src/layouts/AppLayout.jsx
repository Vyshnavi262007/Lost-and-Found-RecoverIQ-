import { useState } from 'react';
import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom';
import { BarChart3, Bell, Bookmark, Boxes, ClipboardCheck, FileSearch, Flag, Gavel, Handshake, Home, LayoutDashboard, ListChecks, LogOut, MapPin, Menu, MessageSquare, PlusCircle, ScrollText, Settings, ShieldCheck, Sparkles, Tags, UserCheck, UserCircle, Users, X } from 'lucide-react';
import Logo from '../components/Logo.jsx';
import NotificationBell from '../components/NotificationBell.jsx';
import { useAuth, homeFor } from '../context/AuthContext.jsx';

const COMMON = [
  { to: '/feed', label: 'Community feed', icon: FileSearch },
  { to: '/report/new?type=lost', label: 'Report lost item', icon: PlusCircle },
  { to: '/report/new?type=found', label: 'Report found item', icon: PlusCircle },
  { to: '/my-reports', label: 'My reports', icon: ListChecks },
  { to: '/matches', label: 'Smart matches', icon: Sparkles },
  { to: '/messages', label: 'Messages', icon: MessageSquare },
  { to: '/my-claims', label: 'My claims', icon: ClipboardCheck },
  { to: '/bookmarks', label: 'Bookmarks', icon: Bookmark },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/profile', label: 'Profile & settings', icon: UserCircle },
];

function sections(role) {
  if (role === 'admin') {
    return [
      { title: 'Administration', items: [
        { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
        { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
        { to: '/admin/users', label: 'Users', icon: Users },
        { to: '/admin/staff-approvals', label: 'Staff approvals', icon: UserCheck },
        { to: '/admin/moderation', label: 'Report moderation', icon: ShieldCheck },
        { to: '/admin/abuse', label: 'Abuse reports', icon: Flag },
        { to: '/admin/disputes', label: 'Claim disputes', icon: Gavel },
        { to: '/admin/categories', label: 'Categories', icon: Tags },
        { to: '/admin/locations', label: 'Campus locations', icon: MapPin },
        { to: '/admin/audit', label: 'Audit logs', icon: ScrollText },
        { to: '/admin/settings', label: 'System settings', icon: Settings },
      ] },
      { title: 'Campus', items: COMMON.filter((i) => ['/feed', '/notifications', '/profile'].includes(i.to)) },
    ];
  }
  if (role === 'staff') {
    return [
      { title: 'Lost-property desk', items: [
        { to: '/staff', label: 'Staff dashboard', icon: LayoutDashboard, end: true },
        { to: '/staff/inventory', label: 'Inventory', icon: Boxes },
        { to: '/staff/claims', label: 'Claims review', icon: ClipboardCheck },
        { to: '/staff/handovers', label: 'Handover history', icon: Handshake },
      ] },
      { title: 'Campus', items: COMMON.filter((i) => !['/my-claims'].includes(i.to)) },
    ];
  }
  return [{ title: null, items: [{ to: '/dashboard', label: 'Dashboard', icon: Home, end: true }, ...COMMON] }];
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const roleLabel = user.role === 'admin' ? 'Administrator' : user.role === 'staff' ? user.staff_title || 'Campus staff' : user.role === 'faculty' ? 'Faculty' : 'Student';

  const sidebar = (
    <nav className="space-y-5 p-3" aria-label="Main">
      {sections(user.role).map((s, i) => (
        <div key={i}>
          {s.title && <p className="mb-1 px-3 text-xs font-semibold text-slate-400">{s.title}</p>}
          <ul className="space-y-0.5">
            {s.items.map((it) => (
              <li key={it.to}>
                <NavLink to={it.to} end={it.end} onClick={() => setOpen(false)}
                  className={({ isActive }) => `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm ${isActive && !it.to.includes('?') ? 'bg-navy-50 font-medium text-navy-800' : 'text-slate-600 hover:bg-slate-50 hover:text-navy-800'}`}>
                  <it.icon className="h-4 w-4" /> {it.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-3">
            <button className="rounded-lg p-2 text-navy-700 hover:bg-navy-50 lg:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu" aria-expanded={open}>
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <Logo to={homeFor(user)} />
          </div>
          <div className="flex items-center gap-2">
            <NotificationBell />
            <Link to="/profile" className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight text-navy-900">{user.full_name}</p>
              <p className="text-xs leading-tight text-slate-500">{roleLabel}</p>
            </Link>
            <button className="btn-ghost" onClick={async () => { await logout(); nav('/'); }} aria-label="Log out"><LogOut className="h-4 w-4" /><span className="hidden sm:inline">Log out</span></button>
          </div>
        </div>
      </header>
      <div className="flex">
        <aside className="sticky top-[53px] hidden h-[calc(100vh-53px)] w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-white lg:block">{sidebar}</aside>
        {open && <aside className="fixed inset-x-0 bottom-0 top-[53px] z-20 overflow-y-auto bg-white lg:hidden">{sidebar}</aside>}
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8"><div className="mx-auto max-w-6xl"><Outlet /></div></main>
      </div>
    </div>
  );
}
