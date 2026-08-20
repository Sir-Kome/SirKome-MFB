import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AccountBalanceWallet, ArrowCircleDown, ArrowCircleUp, AutoAwesome, Delete, History, Send, TrendingUp } from '@mui/icons-material';

import BalanceCard from '../components/BalanceCard';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

const quickActions = [
  { label: 'Send', icon: <Send fontSize="small" />, accent: 'from-cyan-500 to-blue-600' },
  { label: 'Top up', icon: <ArrowCircleDown fontSize="small" />, accent: 'from-violet-500 to-fuchsia-600' },
  { label: 'Withdraw', icon: <ArrowCircleUp fontSize="small" />, accent: 'from-emerald-500 to-teal-600' },
];

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
    } catch {
      return null;
    }
  });
  const [transactions, setTransactions] = useState([]);
  const [adminUserId, setAdminUserId] = useState('');
  const [adminMessage, setAdminMessage] = useState('');
  const [adminActionBusy, setAdminActionBusy] = useState(false);
  const [adminPage, setAdminPage] = useState(1);
  const [users, setUsers] = useState([]);
  const [pageMeta, setPageMeta] = useState({ page: 1, per_page: 10, total: 0, pages: 1 });
  const [freezeReason, setFreezeReason] = useState('');

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token || !user) {
      sessionStorage.removeItem('sirkome_token');
      sessionStorage.removeItem('sirkome_user');
      navigate('/login');
      return;
    }

    Promise.all([
      api.get('/accounts', { headers: { Authorization: `Bearer ${token}` } }),
      api.get('/transactions', {
        params: { page: 1, per_page: 5 },
        headers: { Authorization: `Bearer ${token}` },
      }),
      user.is_admin ? api.get('/admin/users', {
        params: { page: adminPage, per_page: 10 },
        headers: { Authorization: `Bearer ${token}` },
      }) : Promise.resolve({ data: { items: [] } }),
    ])
      .then(([accountsResponse, transactionsResponse, usersResponse]) => {
        setTransactions(transactionsResponse.data?.items || []);
        if (user.is_admin) {
          const nextUsers = Array.isArray(usersResponse.data?.items) ? usersResponse.data.items : [];
          setUsers(nextUsers);
          setPageMeta({
            page: usersResponse.data?.page || 1,
            per_page: usersResponse.data?.per_page || 10,
            total: usersResponse.data?.total || 0,
            pages: usersResponse.data?.pages || 1,
          });
        }
        if (accountsResponse.data?.[0]?.account_number) {
          setUser((current) => current ? { ...current, balance: accountsResponse.data[0].balance } : current);
        }
      })
      .catch(() => {
        sessionStorage.removeItem('sirkome_token');
        sessionStorage.removeItem('sirkome_user');
        navigate('/login');
      });
  }, [navigate, user, adminPage]);

  const selectedUser = users.find((entry) => entry.user_id === adminUserId || String(entry.id) === adminUserId || entry.account_number === adminUserId) || null;

  const handleUserFreeze = async (freezeUser, reasonOverride) => {
    if (!adminUserId.trim()) {
      setAdminMessage('Select a customer from the list first.');
      return;
    }

    if (!selectedUser) {
      setAdminMessage('That user is not available in the admin list.');
      return;
    }

    const nextReason = reasonOverride ?? freezeReason.trim();
    if (freezeUser && !nextReason) {
      setAdminMessage('Add a reason before freezing this account.');
      return;
    }

    setAdminActionBusy(true);
    setAdminMessage('');

    try {
      const token = sessionStorage.getItem('sirkome_token');
      const response = await api.patch(`/admin/users/${encodeURIComponent(selectedUser.user_id || selectedUser.account_number || String(selectedUser.id))}/freeze`, {
        is_frozen: freezeUser,
        reason: freezeUser ? nextReason : '',
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const updatedUser = response.data?.user;
      setAdminMessage(response.data?.message || 'Customer status updated.');
      setUsers((current) => current.map((entry) => (
        entry.user_id === selectedUser.user_id || String(entry.id) === String(selectedUser.id)
          ? { ...entry, is_frozen: Boolean(updatedUser?.is_frozen ?? freezeUser), freeze_reason: updatedUser?.freeze_reason || (freezeUser ? nextReason : null) }
          : entry
      )));
      if (updatedUser) {
        setUser((current) => current ? { ...current, is_frozen: Boolean(updatedUser.is_frozen), freeze_reason: updatedUser.freeze_reason || null } : current);
      }
      setFreezeReason('');
      setAdminUserId('');
    } catch (error) {
      setAdminMessage(error.response?.data?.detail || 'Unable to update the selected user status.');
    } finally {
      setAdminActionBusy(false);
    }
  };

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_35%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />

        <main className="flex-1 space-y-4">
          <Navbar user={user} />

          {user.is_frozen ? (
            <div className="rounded-[24px] border border-amber-200 bg-amber-50 px-5 py-4 text-amber-900 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-wide">Account frozen</p>
              <p className="mt-1 text-sm">
                Your account has been frozen for: {user.freeze_reason || 'No reason provided'}. Please contact support for assistance.
              </p>
            </div>
          ) : null}

          <div className="grid gap-4 2xl:grid-cols-[1.25fr_0.8fr]">
            <div className="space-y-4">
              <BalanceCard
                balance={user.balance}
                accountNumber={user.account_number}
                userName={user.name}
                onSend={() => navigate('/transfer', { state: { fromAccount: user.account_number } })}
              />

              <section className="rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Quick actions</p>
                    <h2 className="text-lg font-semibold text-slate-900">Move money fast</h2>
                  </div>
                  <div className="rounded-2xl bg-cyan-50 p-2 text-cyan-600">
                    <AutoAwesome fontSize="small" />
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  {quickActions.map((action) => {
                    const handleClick = () => {
                      if (action.label === 'Send') {
                        navigate('/transfer');
                      }
                    };

                    return (
                      <button
                        key={action.label}
                        onClick={handleClick}
                        className={`flex items-center gap-2 rounded-2xl bg-gradient-to-r px-4 py-3 text-sm font-medium text-white shadow-lg ${action.accent}`}
                      >
                        {action.icon}
                        {action.label}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Activity</p>
                    <h2 className="text-lg font-semibold text-slate-900">Recent transactions</h2>
                  </div>
                  <button
                    onClick={() => navigate('/transactions')}
                    className="text-sm font-medium text-cyan-600"
                  >
                    View all
                  </button>
                </div>

                <div className="space-y-3">
                  {transactions.map((item, index) => (
                    <div key={`${item.description}-${index}`} className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-2xl bg-slate-900 p-2 text-white">
                          <History fontSize="small" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">{item.description}</p>
                          <p className="text-sm text-slate-500">{item.date}</p>
                        </div>
                      </div>
                      <span className={`font-semibold ${item.type === 'credit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                        {item.type === 'credit' ? '+' : '-'}₦{item.amount.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="space-y-4">
              {user?.is_admin ? (
                <section className="rounded-[28px] border border-rose-200/70 bg-white/80 p-5 shadow-lg backdrop-blur">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Admin tools</p>
                      <h2 className="text-lg font-semibold text-slate-900">Customer management</h2>
                    </div>
                    <div className="rounded-2xl bg-rose-50 p-2 text-rose-600">
                      <Delete fontSize="small" />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="max-h-52 space-y-2 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      {users.length === 0 ? (
                        <p className="text-sm text-slate-500">No customer records loaded.</p>
                      ) : (
                        users.map((entry) => (
                          <button
                            key={entry.user_id || entry.id}
                            type="button"
                            onClick={() => setAdminUserId(entry.user_id || entry.account_number || String(entry.id))}
                            className={`block w-full rounded-xl px-3 py-2 text-left text-sm shadow-sm transition ${
                              adminUserId === (entry.user_id || entry.account_number || String(entry.id))
                                ? 'bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200'
                                : 'bg-white text-slate-700 hover:bg-slate-100'
                            }`}
                          >
                            <span className="font-semibold">{entry.name}</span>
                            <span className="block text-slate-500">{entry.email}</span>
                            <span className="block text-slate-400">{entry.account_number}</span>
                            <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${entry.is_frozen ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                              {entry.is_frozen ? 'Frozen' : 'Active'}
                            </span>
                          </button>
                        ))
                      )}
                    </div>

                    <label className="block text-sm font-medium text-slate-700" htmlFor="admin-user-id">
                      Selected customer
                    </label>
                    <input
                      id="admin-user-id"
                      value={adminUserId}
                      onChange={(event) => setAdminUserId(event.target.value)}
                      placeholder="Select a customer"
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                    />

                    {selectedUser ? (
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                        <p><span className="font-medium">Name:</span> {selectedUser.name}</p>
                        <p><span className="font-medium">Email:</span> {selectedUser.email}</p>
                        <p><span className="font-medium">Account:</span> {selectedUser.account_number}</p>
                        <p><span className="font-medium">Status:</span> {selectedUser.is_frozen ? 'Frozen' : 'Active'}</p>
                      </div>
                    ) : null}

                    <textarea
                      value={freezeReason}
                      onChange={(event) => setFreezeReason(event.target.value)}
                      rows={3}
                      placeholder="Enter a freeze reason for this customer"
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm"
                    />

                    <div className="grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => handleUserFreeze(true, freezeReason)}
                        disabled={adminActionBusy}
                        className="rounded-2xl bg-amber-500 px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {adminActionBusy ? 'Updating...' : 'Freeze account'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUserFreeze(false, '')}
                        disabled={adminActionBusy}
                        className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {adminActionBusy ? 'Updating...' : 'Unfreeze'}
                      </button>
                    </div>

                    <div className="flex items-center justify-between text-sm text-slate-600">
                      <button type="button" onClick={() => setAdminPage((current) => Math.max(1, current - 1))} disabled={adminPage <= 1} className="disabled:opacity-50">Previous</button>
                      <span>Page {pageMeta.page} / {pageMeta.pages}</span>
                      <button type="button" onClick={() => setAdminPage((current) => Math.min(pageMeta.pages, current + 1))} disabled={adminPage >= pageMeta.pages} className="disabled:opacity-50">Next</button>
                    </div>

                    {adminMessage ? <p className="text-sm text-slate-700">{adminMessage}</p> : null}
                  </div>
                </section>
              ) : null}
              <section className="rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Budget</p>
                    <h2 className="text-lg font-semibold text-slate-900">Monthly goals</h2>
                  </div>
                  <div className="rounded-2xl bg-emerald-50 p-2 text-emerald-600">
                    <TrendingUp />
                  </div>
                </div>
                <div className="mt-4 h-2 rounded-full bg-slate-100">
                  <div className="h-2 w-3/4 rounded-full bg-gradient-to-r from-cyan-500 to-violet-500" />
                </div>
                <p className="mt-3 text-sm text-slate-500">You are 75% towards your savings target.</p>
              </section>

              <section className="rounded-[28px] border border-slate-200/70 bg-slate-950 p-5 text-white shadow-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-400">Virtual card</p>
                    <h2 className="text-lg font-semibold">Platinum Visa</h2>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-2">
                    <AccountBalanceWallet />
                  </div>
                </div>
                <div className="mt-4 rounded-3xl bg-gradient-to-br from-cyan-400 to-violet-500 p-4">
                  <p className="text-sm">**** 4821</p>
                  <div className="mt-6 flex items-center justify-between text-sm">
                    <span>{user?.name || 'Cardholder'}</span>
                    <span>09/28</span>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;