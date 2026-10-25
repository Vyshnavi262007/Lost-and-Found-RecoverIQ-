import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import PublicLayout from './layouts/PublicLayout.jsx';
import AppLayout from './layouts/AppLayout.jsx';
import { Spinner } from './components/ui.jsx';

import Landing from './pages/public/Landing.jsx';
import { Login, Register, VerifyEmail } from './pages/public/AuthPages.jsx';
import { Privacy, Terms } from './pages/public/Legal.jsx';
import StudentDashboard from './pages/student/StudentDashboard.jsx';
import Feed from './pages/student/Feed.jsx';
import ReportForm from './pages/student/ReportForm.jsx';
import ReportDetail from './pages/student/ReportDetail.jsx';
import { ReportMatches, AllMatches } from './pages/student/Matches.jsx';
import Notifications from './pages/student/Notifications.jsx';
import { MessageList, Conversation } from './pages/student/Messages.jsx';
import { MyReports, Bookmarks } from './pages/student/MyReports.jsx';
import { MyClaims, ClaimDetail } from './pages/student/Claims.jsx';
import Profile from './pages/student/Profile.jsx';
import StaffDashboard from './pages/staff/StaffDashboard.jsx';
import { Inventory, InventoryForm, InventoryDetail } from './pages/staff/Inventory.jsx';
import { ClaimsReview, Handovers } from './pages/staff/ClaimsReview.jsx';
import AdminDashboard from './pages/admin/AdminDashboard.jsx';
import Analytics from './pages/admin/Analytics.jsx';
import { Users, StaffApprovals } from './pages/admin/Users.jsx';
import { Moderation, AbuseReports, Disputes } from './pages/admin/Moderation.jsx';
import { Categories, Locations } from './pages/admin/Catalog.jsx';
import { AuditLogs, SystemSettings } from './pages/admin/System.jsx';

function Guard({ roles, children }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname + loc.search }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/feed" replace />;
  return children;
}

export default function App() {
  const any = (el) => <Guard>{el}</Guard>;
  const staff = (el) => <Guard roles={['staff', 'admin']}>{el}</Guard>;
  const admin = (el) => <Guard roles={['admin']}>{el}</Guard>;
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
      </Route>
      <Route element={<Guard><AppLayout /></Guard>}>
        <Route path="/dashboard" element={<Guard roles={['student', 'faculty']}><StudentDashboard /></Guard>} />
        <Route path="/feed" element={any(<Feed />)} />
        <Route path="/report/new" element={any(<ReportForm />)} />
        <Route path="/reports/:id" element={any(<ReportDetail />)} />
        <Route path="/reports/:id/edit" element={any(<ReportForm edit />)} />
        <Route path="/reports/:id/matches" element={any(<ReportMatches />)} />
        <Route path="/matches" element={any(<AllMatches />)} />
        <Route path="/notifications" element={any(<Notifications />)} />
        <Route path="/messages" element={any(<MessageList />)} />
        <Route path="/messages/:id" element={any(<Conversation />)} />
        <Route path="/my-reports" element={any(<MyReports />)} />
        <Route path="/bookmarks" element={any(<Bookmarks />)} />
        <Route path="/my-claims" element={any(<MyClaims />)} />
        <Route path="/claims/:id" element={any(<ClaimDetail />)} />
        <Route path="/profile" element={any(<Profile />)} />

        <Route path="/staff" element={staff(<StaffDashboard />)} />
        <Route path="/staff/inventory" element={staff(<Inventory />)} />
        <Route path="/staff/inventory/new" element={staff(<InventoryForm />)} />
        <Route path="/staff/inventory/:id" element={staff(<InventoryDetail />)} />
        <Route path="/staff/claims" element={staff(<ClaimsReview />)} />
        <Route path="/staff/handovers" element={staff(<Handovers />)} />

        <Route path="/admin" element={admin(<AdminDashboard />)} />
        <Route path="/admin/analytics" element={admin(<Analytics />)} />
        <Route path="/admin/users" element={admin(<Users />)} />
        <Route path="/admin/staff-approvals" element={admin(<StaffApprovals />)} />
        <Route path="/admin/moderation" element={admin(<Moderation />)} />
        <Route path="/admin/abuse" element={admin(<AbuseReports />)} />
        <Route path="/admin/disputes" element={admin(<Disputes />)} />
        <Route path="/admin/categories" element={admin(<Categories />)} />
        <Route path="/admin/locations" element={admin(<Locations />)} />
        <Route path="/admin/audit" element={admin(<AuditLogs />)} />
        <Route path="/admin/settings" element={admin(<SystemSettings />)} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
