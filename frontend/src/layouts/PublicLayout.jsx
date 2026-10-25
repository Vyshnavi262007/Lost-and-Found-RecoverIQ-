import { Link, Outlet } from 'react-router-dom';
import Logo from '../components/Logo.jsx';
import { useAuth, homeFor } from '../context/AuthContext.jsx';

export default function PublicLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Logo />
          <nav className="flex items-center gap-2">
            {user ? (
              <Link to={homeFor(user)} className="btn-primary">Open my dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost">Log in</Link>
                <Link to="/register" className="btn-primary">Create account</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm text-slate-500">
          <Logo />
          <nav className="flex flex-wrap gap-4" aria-label="Footer">
            <a className="hover:text-navy-700" href="mailto:lostandfound@campus.example.edu">Contact support</a>
            <Link className="hover:text-navy-700" to="/privacy">Privacy</Link>
            <Link className="hover:text-navy-700" to="/terms">Terms</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
