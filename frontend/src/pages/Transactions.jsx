import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowBack, History } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Transactions() {
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

    api.get('/transactions', { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        setTransactions(response.data);
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

          <section className="rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">History</p>
                <h2 className="text-lg font-semibold text-slate-900">All transactions</h2>
              </div>
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
              >
                <ArrowBack fontSize="small" />
                Back
              </button>
            </div>

            {transactions.length === 0 ? (
              <div className="rounded-2xl bg-slate-50 p-6 text-center text-sm text-slate-500">
                No transactions yet.
              </div>
            ) : (
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
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

export default Transactions;
