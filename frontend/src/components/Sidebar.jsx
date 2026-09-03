import { AccountBalance, AdminPanelSettings, History, Home, Logout, People, Send } from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

const customerMenuItems = [
  { label: 'Dashboard', icon: <Home fontSize="small" />, path: '/dashboard' },
  { label: 'Accounts', icon: <AccountBalance fontSize="small" />, path: '/accounts' },
  { label: 'Transfer', icon: <Send fontSize="small" />, path: '/transfer' },
  { label: 'Transactions', icon: <History fontSize="small" />, path: '/transactions' },
];

const adminMenuItems = [
  { label: 'Admin dashboard', icon: <AdminPanelSettings fontSize="small" />, path: '/admin-dashboard' },
  { label: 'Transfer', icon: <Send fontSize="small" />, path: '/transfer' },
  { label: 'User management', icon: <People fontSize="small" />, path: '/admin/users' },
];

function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const menuItems = user?.is_admin ? adminMenuItems : customerMenuItems;

  const handleLogout = () => {
    sessionStorage.removeItem('sirkome_token');
    sessionStorage.removeItem('sirkome_user');
    navigate('/login');
  };

  return (
    <aside className="w-full rounded-[28px] bg-slate-950 p-6 text-white shadow-2xl xl:w-72">
      <div className="mb-8 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/profile')} aria-label="Open profile" title="Open profile" className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 via-sky-500 to-violet-500 font-semibold transition hover:scale-105">
          <span className="text-base leading-none">SB</span>
          <span className="mt-1 text-[9px] font-medium uppercase tracking-wide text-white/80">{user?.tier || 'Tier 1'}</span>
        </button>
        <div>
          <p className="text-sm text-slate-400">{user?.is_admin ? 'Operations' : 'Personal banking'}</p>
          <h2 className="text-lg font-semibold">SirKome Bank</h2>
        </div>
      </div>

      <nav className="space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.label}
            onClick={() => navigate(item.path)}
            className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm transition ${
              location.pathname === item.path || (item.path === '/dashboard' && location.pathname === '/')
                ? 'bg-white/10 text-white'
                : 'text-slate-300 hover:bg-white/10 hover:text-white'
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="mt-10 rounded-3xl border border-white/10 bg-white/10 p-4 backdrop-blur">
        <p className="text-sm text-slate-300">{user?.is_admin ? 'Admin workspace' : 'Spending insight'}</p>
        <p className="mt-2 text-3xl font-semibold">{user?.is_admin ? 'Secure' : '₦1,280'}</p>
        <p className="mt-1 text-sm text-emerald-300">{user?.is_admin ? 'Protected access' : 'Up 12% this month'}</p>
      </div>

      <button
        onClick={handleLogout}
        className="mt-6 flex w-full items-center gap-3 rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white"
      >
        <Logout fontSize="small" />
        <span>Logout</span>
      </button>
    </aside>
  );
}

export default Sidebar;