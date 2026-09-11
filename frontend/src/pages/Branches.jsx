import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { AddBusiness, ToggleOff, ToggleOn } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Branches() {
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const token = sessionStorage.getItem('sirkome_token');
  const canView = Boolean(user?.permissions?.includes('view_branches') || user?.permissions?.includes('view_assigned_branch'));
  const canManage = Boolean(user?.permissions?.includes('manage_branches'));
  const [branches, setBranches] = useState([]);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({ branch_code: '', name: '', address: '', city: '', state: '', phone: '', email: '' });

  useEffect(() => {
    if (!token || !canView) return;
    api.get('/branches', { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => setBranches(response.data || []))
      .catch((error) => setMessage(error.response?.data?.detail || 'Unable to load branches.'));
  }, [canView, token]);

  if (!user || !token) return <Navigate to="/staff/login" replace />;
  if (!canView) return <Navigate to="/staff/dashboard" replace />;

  const submit = async (event) => {
    event.preventDefault();
    try {
      await api.post('/branches', form, { headers: { Authorization: `Bearer ${token}` } });
      setForm({ branch_code: '', name: '', address: '', city: '', state: '', phone: '', email: '' });
      setMessage('Branch created successfully.');
      const response = await api.get('/branches', { headers: { Authorization: `Bearer ${token}` } });
      setBranches(response.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to create branch.');
    }
  };

  const toggleStatus = async (branch) => {
    try {
      await api.patch(`/branches/${branch.id}/status`, { is_active: !branch.is_active }, { headers: { Authorization: `Bearer ${token}` } });
      setMessage('Branch status updated.');
      const response = await api.get('/branches', { headers: { Authorization: `Bearer ${token}` } });
      setBranches(response.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to update branch status.');
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.16),_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg sm:p-6">
            <div className="flex items-center justify-between gap-4"><div><p className="text-sm font-medium uppercase tracking-wide text-cyan-600">Network</p><h1 className="mt-1 text-2xl font-semibold text-slate-950">Branches</h1><p className="mt-1 text-sm text-slate-500">View branches within your authorized scope.</p></div><AddBusiness className="text-cyan-600" sx={{ fontSize: 40 }} /></div>
            {canManage ? <form onSubmit={submit} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2 xl:grid-cols-4"><input required value={form.branch_code} onChange={(event) => setForm({ ...form, branch_code: event.target.value })} placeholder="Branch code" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Branch name" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input required value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} placeholder="Address" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input required value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} placeholder="City" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input required value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value })} placeholder="State" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input required value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Phone" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email (optional)" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><button type="submit" className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Create branch</button></form> : null}
            {message ? <p className="mt-3 text-sm font-medium text-slate-700">{message}</p> : null}
          </section>
          <section className="grid gap-3 md:grid-cols-2">{branches.map((branch) => <article key={branch.id} className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-lg"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-cyan-600">{branch.branch_code}</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{branch.name}</h2><p className="mt-1 text-sm text-slate-500">{branch.address}, {branch.city}, {branch.state}</p><p className="mt-1 text-sm text-slate-400">{branch.phone}{branch.email ? ` · ${branch.email}` : ''}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${branch.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>{branch.is_active ? 'Active' : 'Inactive'}</span></div>{canManage ? <button type="button" onClick={() => toggleStatus(branch)} className="mt-4 flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">{branch.is_active ? <ToggleOff fontSize="small" /> : <ToggleOn fontSize="small" />}{branch.is_active ? 'Deactivate' : 'Activate'}</button> : null}</article>)}{branches.length === 0 ? <p className="col-span-full py-8 text-center text-sm text-slate-500">No branches in your authorized scope.</p> : null}</section>
        </main>
      </div>
    </div>
  );
}

export default Branches;
