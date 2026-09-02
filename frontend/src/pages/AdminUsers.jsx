import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ContentCopy, Delete, LockOpen, PauseCircle, People } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function AdminUsers() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const [users, setUsers] = useState([]);
  const [pageMeta, setPageMeta] = useState({ page: 1, pages: 1, total: 0 });
  const [page, setPage] = useState(1);
  const [reason, setReason] = useState({});
  const [busyId, setBusyId] = useState('');
  const [message, setMessage] = useState('');
  const [copiedAccount, setCopiedAccount] = useState('');

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token || !user?.is_admin) {
      navigate('/login');
      return;
    }

    api.get('/admin/users', { params: { page, per_page: 10 }, headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        setUsers(response.data?.items || []);
        setPageMeta({ page: response.data?.page || page, pages: response.data?.pages || 1, total: response.data?.total || 0 });
      })
      .catch(() => navigate('/login'));
  }, [navigate, page, user?.is_admin]);

  const updateFreeze = async (entry, isFrozen) => {
    const identifier = entry.user_id || entry.account_number || String(entry.id);
    const freezeReason = (reason[identifier] || '').trim();
    if (isFrozen && !freezeReason) {
      setMessage('A reason is required before freezing an account.');
      return;
    }
    setBusyId(identifier);
    setMessage('');
    try {
      const token = sessionStorage.getItem('sirkome_token');
      const response = await api.patch(`/admin/users/${encodeURIComponent(identifier)}/freeze`, { is_frozen: isFrozen, reason: isFrozen ? freezeReason : '' }, { headers: { Authorization: `Bearer ${token}` } });
      const updated = response.data?.user;
      setUsers((current) => current.map((item) => item.user_id === entry.user_id ? { ...item, is_frozen: Boolean(updated?.is_frozen ?? isFrozen), freeze_reason: updated?.freeze_reason || null } : item));
      setReason((current) => ({ ...current, [identifier]: '' }));
      setMessage(response.data?.message || 'Account status updated.');
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to update account status.');
    } finally {
      setBusyId('');
    }
  };

  const deleteUser = async (entry) => {
    if (entry.is_admin || !window.confirm(`Delete ${entry.name}'s account permanently?`)) return;
    const identifier = entry.user_id || entry.account_number || String(entry.id);
    setBusyId(identifier);
    setMessage('');
    try {
      const token = sessionStorage.getItem('sirkome_token');
      const response = await api.delete(`/admin/users/${encodeURIComponent(identifier)}`, { headers: { Authorization: `Bearer ${token}` } });
      setUsers((current) => current.filter((item) => item.user_id !== entry.user_id));
      setPageMeta((current) => ({ ...current, total: Math.max(0, current.total - 1) }));
      setMessage(response.data?.message || 'User deleted successfully.');
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to delete this account.');
    } finally {
      setBusyId('');
    }
  };

  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_admin) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(244,63,94,0.16),_transparent_35%),linear-gradient(135deg,_#fff7f5_0%,_#f1f5f9_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] border border-rose-200/70 bg-white/85 p-5 shadow-lg backdrop-blur sm:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <p className="text-sm font-medium uppercase tracking-wide text-rose-600">Admin tools</p>
                <h1 className="mt-1 text-2xl font-semibold text-slate-950">Customer directory</h1>
                <p className="mt-1 text-sm text-slate-500">{pageMeta.total} registered accounts</p>
              </div>
              <People className="text-rose-500" sx={{ fontSize: 40 }} />
            </div>

            <div className="mt-6 space-y-3">
              {users.map((entry) => {
                const identifier = entry.user_id || entry.account_number || String(entry.id);
                const isBusy = busyId === identifier;
                return (
                  <article key={identifier} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="font-semibold text-slate-900">{entry.name}</h2>
                          <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${entry.is_frozen ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{entry.is_frozen ? 'Frozen' : 'Active'}</span>
                          {entry.is_admin ? <span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600">Admin</span> : null}
                        </div>
                        <p className="mt-1 truncate text-sm text-slate-500">{entry.email}</p>
                        <div className="mt-1 flex items-center gap-2 text-sm text-slate-400">
                          <span>{entry.account_number || 'No account number'}</span>
                          <button
                            type="button"
                            aria-label="Copy account number"
                            title="Copy account number"
                            onClick={async () => {
                              if (!entry.account_number) return;
                              try {
                                await navigator.clipboard.writeText(entry.account_number);
                                setCopiedAccount(entry.account_number);
                                window.setTimeout(() => setCopiedAccount(''), 1200);
                              } catch {
                                setCopiedAccount('');
                              }
                            }}
                            className="rounded-xl p-1 transition hover:bg-slate-200"
                          >
                            <ContentCopy fontSize="small" />
                          </button>
                          {copiedAccount === entry.account_number ? <span className="text-[10px] uppercase tracking-wide text-emerald-600">Copied</span> : null}
                        </div>
                        <p className="text-sm text-slate-400">{entry.currency} {Number(entry.balance || 0).toFixed(2)}</p>
                      </div>
                      {!entry.is_admin ? (
                        <div className="flex flex-col gap-2 sm:flex-row">
                          {entry.is_frozen ? (
                            <button type="button" onClick={() => updateFreeze(entry, false)} disabled={isBusy} className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"><LockOpen fontSize="small" />Unfreeze</button>
                          ) : (
                            <div className="flex gap-2">
                              <input value={reason[identifier] || ''} onChange={(event) => setReason((current) => ({ ...current, [identifier]: event.target.value }))} placeholder="Freeze reason" className="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
                              <button type="button" onClick={() => updateFreeze(entry, true)} disabled={isBusy} title="Freeze account" aria-label="Freeze account" className="rounded-xl bg-amber-500 px-3 py-2 text-white hover:bg-amber-600 disabled:opacity-50"><PauseCircle fontSize="small" /></button>
                            </div>
                          )}
                          <button type="button" onClick={() => deleteUser(entry)} disabled={isBusy} title="Delete account" aria-label="Delete account" className="flex items-center justify-center gap-2 rounded-xl bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-50"><Delete fontSize="small" />Delete</button>
                        </div>
                      ) : <span className="text-sm text-slate-400">Protected account</span>}
                    </div>
                  </article>
                );
              })}
            </div>

            <div className="mt-5 flex items-center justify-between text-sm text-slate-600">
              <button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1} className="rounded-lg px-2 py-1 hover:bg-slate-100 disabled:opacity-40">Previous</button>
              <span>Page {pageMeta.page} / {pageMeta.pages}</span>
              <button type="button" onClick={() => setPage((current) => Math.min(pageMeta.pages, current + 1))} disabled={page >= pageMeta.pages} className="rounded-lg px-2 py-1 hover:bg-slate-100 disabled:opacity-40">Next</button>
            </div>
            {message ? <p className="mt-4 text-sm font-medium text-slate-700">{message}</p> : null}
          </section>
        </main>
      </div>
    </div>
  );
}

export default AdminUsers;
