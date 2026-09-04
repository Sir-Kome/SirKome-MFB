import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AdminPanelSettings, ArrowForward, Group, History, Security, Send, Visibility, VisibilityOff } from '@mui/icons-material';

import AccountNumberCopy from '../components/AccountNumberCopy';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function AdminDashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const [summary, setSummary] = useState({ total: 0, frozen: 0, admins: 0 });
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [showAdminBalance, setShowAdminBalance] = useState(false);
  const [showAdminAccountNumber, setShowAdminAccountNumber] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token || !user?.is_admin) {
      navigate('/login');
      return;
    }

    Promise.all([
      api.get('/admin/users', {
        params: { page: 1, per_page: 100 },
        headers: { Authorization: `Bearer ${token}` },
      }),
      api.get('/transactions', {
        params: { page: 1, per_page: 5 },
        headers: { Authorization: `Bearer ${token}` },
      }),
    ])
      .then(([usersResponse, transactionsResponse]) => {
        const users = usersResponse.data?.items || usersResponse.data || [];
        setAccounts(users);
        setSummary({
          total: usersResponse.data?.total || users.length,
          frozen: users.filter((entry) => entry.is_frozen).length,
          admins: users.filter((entry) => entry.is_admin).length,
        });
        setTransactions(transactionsResponse.data?.items || []);
      })
      .catch(() => navigate('/login'));
  }, [navigate, user?.is_admin]);

  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(244,63,94,0.16),_transparent_35%),linear-gradient(135deg,_#fff7f5_0%,_#f1f5f9_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] border border-rose-200/70 bg-slate-950 p-6 text-white shadow-xl">
            <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.18em] text-rose-300">Operations console</p>
                <h1 className="mt-2 text-3xl font-semibold">Admin dashboard</h1>
                <p className="mt-2 max-w-xl text-sm text-slate-300">Monitor customer accounts, balances, and recent banking activity from one place.</p>
              </div>
              <AdminPanelSettings className="text-rose-300" sx={{ fontSize: 56 }} />
            </div>
          </section>

          <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg backdrop-blur">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm text-slate-500">Admin account</p>
                <div className="mt-2 flex items-center gap-3">
                  <h2 className="text-2xl font-semibold text-slate-900">{showAdminBalance ? `₦${Number(user.balance || 0).toFixed(2)}` : '••••••'}</h2>
                  <button
                    type="button"
                    aria-label={showAdminBalance ? 'Hide balance' : 'Show balance'}
                    title={showAdminBalance ? 'Hide balance' : 'Show balance'}
                    onClick={() => setShowAdminBalance((current) => !current)}
                    className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-200"
                  >
                    {showAdminBalance ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                  </button>
                </div>
                <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
                  <span>{showAdminAccountNumber ? (user.account_number || 'No account number') : (user.account_number ? `•••• ${user.account_number.slice(-4)}` : '••••')}</span>
                  <button
                    type="button"
                    aria-label={showAdminAccountNumber ? 'Hide account number' : 'Show account number'}
                    title={showAdminAccountNumber ? 'Hide account number' : 'Show account number'}
                    onClick={() => setShowAdminAccountNumber((current) => !current)}
                    className="rounded-xl p-1 transition hover:bg-slate-200"
                  >
                    {showAdminAccountNumber ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                  </button>
                  <AccountNumberCopy accountNumber={user.account_number} />
                </div>
              </div>
              <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-left">
                <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">Available balance</p>
                <p className="mt-1 text-lg font-semibold text-emerald-900">{showAdminBalance ? `₦${Number(user.balance || 0).toFixed(2)}` : '••••••'}</p>
              </div>
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              { label: 'Total accounts', value: summary.total, icon: <Group />, tone: 'bg-cyan-50 text-cyan-700' },
              { label: 'Frozen accounts', value: summary.frozen, icon: <Security />, tone: 'bg-amber-50 text-amber-700' },
              { label: 'Admin accounts', value: summary.admins, icon: <AdminPanelSettings />, tone: 'bg-rose-50 text-rose-700' },
            ].map((item) => (
              <section key={item.label} className="rounded-[24px] border border-slate-200/70 bg-white/85 p-5 shadow-lg backdrop-blur">
                <div className={`mb-5 flex h-11 w-11 items-center justify-center rounded-2xl ${item.tone}`}>{item.icon}</div>
                <p className="text-sm text-slate-500">{item.label}</p>
                <p className="mt-1 text-3xl font-semibold text-slate-950">{item.value}</p>
              </section>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg backdrop-blur">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Accounts</p>
                  <h2 className="text-lg font-semibold text-slate-900">Customer accounts</h2>
                </div>
                <button type="button" onClick={() => navigate('/admin/users')} className="text-sm font-medium text-rose-600">View all</button>
              </div>

              <div className="space-y-3">
                {accounts.length === 0 ? (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">No accounts found.</div>
                ) : (
                  accounts.slice(0, 5).map((account) => (
                    <div key={account.user_id || account.account_number} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-800">{account.name}</p>
                        <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                          <span>{account.account_number ? `•••• ${account.account_number.slice(-4)}` : '••••'}</span>
                          <AccountNumberCopy accountNumber={account.account_number} />
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-slate-900">₦{Number(account.balance || 0).toFixed(2)}</p>
                        <p className="text-xs text-slate-500">{account.is_frozen ? 'Frozen' : 'Active'}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg backdrop-blur">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">Activity</p>
                  <h2 className="text-lg font-semibold text-slate-900">Recent transactions</h2>
                </div>
                <div className="rounded-2xl bg-rose-50 p-2 text-rose-600">
                  <History fontSize="small" />
                </div>
              </div>

              <div className="space-y-3">
                {transactions.length === 0 ? (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">No transactions found.</div>
                ) : (
                  transactions.map((item, index) => (
                    <div key={`${item.description}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium text-slate-800">{item.description}</p>
                        <span className={`font-semibold ${item.type === 'credit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                          {item.type === 'credit' ? '+' : '-'}₦{Number(item.amount || 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
                        <span>{item.account_number || item.related_account || 'Bank transfer'}</span>
                        <span>{item.date}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <button type="button" onClick={() => navigate('/transfer', { state: { fromAccount: user.account_number } })} className="flex w-full items-center justify-between rounded-[24px] border border-emerald-200 bg-gradient-to-r from-emerald-50 to-cyan-50 p-5 text-left shadow-lg transition hover:border-emerald-400 hover:shadow-xl">
              <span>
                <span className="block text-sm font-medium uppercase tracking-wide text-emerald-700">Transfer</span>
                <span className="mt-1 block text-xl font-semibold text-slate-950">Send money to another account</span>
                <span className="mt-1 block text-sm text-slate-500">Use your admin account balance to move funds securely.</span>
              </span>
              <Send className="text-emerald-700" />
            </button>

            <button type="button" onClick={() => navigate('/admin/users')} className="flex w-full items-center justify-between rounded-[24px] border border-rose-200 bg-white p-5 text-left shadow-lg transition hover:border-rose-400 hover:shadow-xl">
              <span>
                <span className="block text-sm font-medium uppercase tracking-wide text-rose-600">Account controls</span>
                <span className="mt-1 block text-xl font-semibold text-slate-950">Open customer directory</span>
                <span className="mt-1 block text-sm text-slate-500">Freeze, unfreeze, or permanently delete customer accounts.</span>
              </span>
              <ArrowForward className="text-rose-600" />
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}

export default AdminDashboard;
