import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AccountBalanceWallet, ArrowCircleDown, ArrowCircleUp, AutoAwesome, History, Send, TrendingUp } from '@mui/icons-material';

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
  const [user] = useState(() => {
    const storedUser = JSON.parse(localStorage.getItem('sirkome_user') || 'null');
    return storedUser;
  });
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('sirkome_token');
    if (!token) {
      navigate('/login');
      return;
    }

    Promise.all([
      api.get('/accounts', { headers: { Authorization: `Bearer ${token}` } }),
      api.get('/transactions', { headers: { Authorization: `Bearer ${token}` } }),
    ])
      .then(([, transactionsResponse]) => {
        setTransactions(transactionsResponse.data);
      })
      .catch(() => {
        localStorage.removeItem('sirkome_token');
        localStorage.removeItem('sirkome_user');
        navigate('/login');
      });
  }, [navigate]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_35%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />

        <main className="flex-1 space-y-4">
          <Navbar user={user} />

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
                        {item.type === 'credit' ? '+' : '-'}${item.amount.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="space-y-4">
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