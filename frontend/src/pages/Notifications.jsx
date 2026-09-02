import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ArrowBack, Close, Notifications as NotificationsIcon } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Notifications() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState({ page: 1, pages: 1, total: 0 });
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token || !user) {
      navigate('/login');
      return;
    }
    api.get('/notifications', { params: { page, per_page: 10 }, headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        setItems(response.data?.items || []);
        setMeta({ page: response.data?.page || page, pages: response.data?.pages || 1, total: response.data?.total || 0 });
      })
      .catch(() => navigate('/login'));
  }, [navigate, page, user]);

  const deleteItem = async (id) => {
    const token = sessionStorage.getItem('sirkome_token');
    await api.delete(`/notifications/${id}`, { headers: { Authorization: `Bearer ${token}` } });
    setItems((current) => current.filter((item) => item.id !== id));
    setMeta((current) => ({ ...current, total: Math.max(0, current.total - 1) }));
  };

  const clearAll = async () => {
    const token = sessionStorage.getItem('sirkome_token');
    await api.delete('/notifications', { headers: { Authorization: `Bearer ${token}` } });
    setItems([]);
    setMeta((current) => ({ ...current, total: 0, pages: 1 }));
    setPage(1);
    setMessage('All notifications cleared.');
  };

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_35%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] border border-slate-200/70 bg-white/85 p-5 shadow-lg backdrop-blur sm:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-3">
                <button type="button" onClick={() => navigate(-1)} aria-label="Go back" title="Go back" className="rounded-xl p-2 text-slate-500 hover:bg-slate-100"><ArrowBack fontSize="small" /></button>
                <div>
                  <p className="text-sm font-medium uppercase tracking-wide text-cyan-600">Inbox</p>
                  <h1 className="mt-1 text-2xl font-semibold text-slate-950">All notifications</h1>
                  <p className="mt-1 text-sm text-slate-500">{meta.total} notifications</p>
                </div>
              </div>
              <button type="button" onClick={clearAll} disabled={meta.total === 0} className="rounded-xl border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-40">Clear all</button>
            </div>

            <div className="mt-6 space-y-3">
              {items.length === 0 ? (
                <div className="rounded-2xl bg-slate-50 px-4 py-12 text-center text-sm text-slate-500"><NotificationsIcon className="mb-2 text-slate-300" /><p>No notifications yet.</p></div>
              ) : items.map((item) => (
                <article key={item.id} className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div>
                    <h2 className="font-semibold text-slate-900">{item.title}</h2>
                    <p className="mt-1 text-sm leading-6 text-slate-600">{item.message}</p>
                    <p className="mt-2 text-xs text-slate-400">{item.created_at}</p>
                  </div>
                  <button type="button" onClick={() => deleteItem(item.id)} aria-label="Delete notification" title="Delete notification" className="shrink-0 rounded-lg p-1 text-slate-400 hover:bg-white hover:text-rose-600"><Close fontSize="small" /></button>
                </article>
              ))}
            </div>

            <div className="mt-5 flex items-center justify-between text-sm text-slate-600">
              <button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1} className="rounded-lg px-2 py-1 hover:bg-slate-100 disabled:opacity-40">Previous</button>
              <span>Page {meta.page} / {meta.pages}</span>
              <button type="button" onClick={() => setPage((current) => Math.min(meta.pages, current + 1))} disabled={page >= meta.pages} className="rounded-lg px-2 py-1 hover:bg-slate-100 disabled:opacity-40">Next</button>
            </div>
            {message ? <p className="mt-4 text-sm font-medium text-emerald-700">{message}</p> : null}
          </section>
        </main>
      </div>
    </div>
  );
}

export default Notifications;
