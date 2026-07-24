import { AccountBalance, History, Home, Logout, Send } from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

const menuItems = [
  { label: 'Dashboard', icon: <Home fontSize="small" />, path: '/dashboard' },
  { label: 'Accounts', icon: <AccountBalance fontSize="small" />, path: '/accounts' },
  { label: 'Transfer', icon: <Send fontSize="small" />, path: '/transfer' },
  { label: 'Transactions', icon: <History fontSize="small" />, path: '/transactions' },
];

function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('sirkome_token');
    localStorage.removeItem('sirkome_user');
    navigate('/login');
  };

  return (
    <aside className="w-full rounded-[28px] bg-slate-950 p-6 text-white shadow-2xl xl:w-72">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 via-sky-500 to-violet-500 font-semibold">
          VB
        </div>
        <div>
          <p className="text-sm text-slate-400">Fintech</p>
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
        <p className="text-sm text-slate-300">Spending insight</p>
        <p className="mt-2 text-3xl font-semibold">+$1,280</p>
        <p className="mt-1 text-sm text-emerald-300">Up 12% this month</p>
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