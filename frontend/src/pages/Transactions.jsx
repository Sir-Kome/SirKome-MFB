import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowBack, History } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Transactions() {
  const navigate = useNavigate();
  const [user] = useState(() => {
    const storedUser = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
    return storedUser;
  });
  const [transactions, setTransactions] = useState([]);
  const [page, setPage] = useState(1);
  const [pageMeta, setPageMeta] = useState({ page: 1, per_page: 10, total: 0, pages: 1 });

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token) {
      navigate('/login');
      return;
    }

    api.get('/transactions', {
      params: { page, per_page: 10 },
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        setTransactions(response.data?.items || []);
        setPageMeta({
          page: response.data?.page || page,
          per_page: response.data?.per_page || 10,
          total: response.data?.total || 0,
          pages: response.data?.pages || 1,
        });
      })
      .catch(() => {
        sessionStorage.removeItem('sirkome_token');
        sessionStorage.removeItem('sirkome_user');
        navigate('/login');
      });
  }, [navigate, page]);

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
                  <div key={`${item.description}-${index}`} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="rounded-2xl bg-slate-900 p-2 text-white">
                        <History fontSize="small" />
                      </div>
                      <div>
                        <p className="break-words font-medium text-slate-800">{item.description}</p>
                        <p className="text-sm text-slate-500">{item.date}</p>
                      </div>
                    </div>
                    <span className={`shrink-0 text-right font-semibold ${item.type === 'credit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                      {item.type === 'credit' ? '+' : '-'}₦{item.amount.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-5 flex items-center justify-between border-t border-slate-200 pt-4 text-sm text-slate-600">
              <button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1} className="font-medium text-cyan-700 disabled:cursor-not-allowed disabled:opacity-40">
                Previous
              </button>
              <span>Page {pageMeta.page} of {pageMeta.pages} · {pageMeta.total} total</span>
              <button type="button" onClick={() => setPage((current) => Math.min(pageMeta.pages, current + 1))} disabled={page >= pageMeta.pages} className="font-medium text-cyan-700 disabled:cursor-not-allowed disabled:opacity-40">
                Next
              </button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default Transactions;
