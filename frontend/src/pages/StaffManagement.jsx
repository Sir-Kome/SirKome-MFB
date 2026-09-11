import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { PersonAdd, ToggleOff, ToggleOn } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

const allRoles = ['SUPER_ADMIN', 'ADMIN', 'BRANCH_MANAGER', 'TELLER', 'ACCOUNT_OFFICER', 'MARKETER'];
const manageableRoles = {
  SUPER_ADMIN: allRoles,
  ADMIN: allRoles.filter((role) => role !== 'SUPER_ADMIN'),
  BRANCH_MANAGER: ['TELLER', 'ACCOUNT_OFFICER', 'MARKETER'],
};

function StaffManagement() {
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const token = sessionStorage.getItem('sirkome_token');
  const canManage = Boolean(user?.permissions?.includes('manage_staff') || user?.permissions?.includes('manage_branch_staff'));
  const [staff, setStaff] = useState([]);
  const [branches, setBranches] = useState([]);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', pin: '', role: manageableRoles[user?.role]?.[0] || 'TELLER', branch_id: '' });

  useEffect(() => {
    if (!token || !canManage) return;
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([api.get('/staff', { headers }), api.get('/branches', { headers })])
      .then(([staffResponse, branchResponse]) => {
        setStaff(staffResponse.data || []);
        setBranches(branchResponse.data || []);
      })
      .catch((error) => setMessage(error.response?.data?.detail || 'Unable to load staff records.'));
  }, [canManage, token]);

  if (!user || !token) return <Navigate to="/staff/login" replace />;
  if (!canManage) return <Navigate to="/staff/dashboard" replace />;

  const roles = manageableRoles[user.role] || [];
  const submit = async (event) => {
    event.preventDefault();
    setMessage('');
    try {
      await api.post('/staff', { ...form, branch_id: form.branch_id ? Number(form.branch_id) : null }, { headers: { Authorization: `Bearer ${token}` } });
      setForm({ name: '', email: '', phone: '', password: '', pin: '', role: roles[0] || 'TELLER', branch_id: '' });
      setMessage('Staff member created successfully.');
      const [staffResponse, branchResponse] = await Promise.all([
        api.get('/staff', { headers: { Authorization: `Bearer ${token}` } }),
        api.get('/branches', { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setStaff(staffResponse.data || []);
      setBranches(branchResponse.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to create staff member.');
    }
  };

  const toggleStatus = async (entry) => {
    try {
      await api.patch(`/staff/${encodeURIComponent(entry.id)}/status`, { is_active: !entry.is_active }, { headers: { Authorization: `Bearer ${token}` } });
      setMessage('Staff status updated.');
      const response = await api.get('/staff', { headers: { Authorization: `Bearer ${token}` } });
      setStaff(response.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to update staff status.');
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.16),_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg sm:p-6">
            <div className="flex items-center justify-between gap-4">
              <div><p className="text-sm font-medium uppercase tracking-wide text-cyan-600">Operations</p><h1 className="mt-1 text-2xl font-semibold text-slate-950">Staff management</h1><p className="mt-1 text-sm text-slate-500">Manage authorized staff without exposing credentials.</p></div>
              <PersonAdd className="text-cyan-600" sx={{ fontSize: 40 }} />
            </div>
            <form onSubmit={submit} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2 xl:grid-cols-4">
              <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Full name" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Phone" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
              <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">{roles.map((role) => <option key={role}>{role}</option>)}</select>
              <input required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Initial password" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input required inputMode="numeric" maxLength="4" value={form.pin} onChange={(event) => setForm({ ...form, pin: event.target.value })} placeholder="Initial PIN" className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" />
              <select value={form.branch_id} onChange={(event) => setForm({ ...form, branch_id: event.target.value })} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"><option value="">No branch assignment</option>{branches.filter((branch) => branch.is_active).map((branch) => <option key={branch.id} value={branch.id}>{branch.branch_code} - {branch.name}</option>)}</select>
              <button type="submit" className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Create staff</button>
            </form>
            {message ? <p className="mt-3 text-sm font-medium text-slate-700">{message}</p> : null}
          </section>
          <section className="space-y-3 rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg sm:p-6">
            {staff.map((entry) => <article key={entry.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-slate-900">{entry.name}</h2><span className="rounded-full bg-cyan-100 px-2 py-1 text-[10px] font-semibold uppercase text-cyan-700">{entry.role}</span><span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${entry.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>{entry.is_active ? 'Active' : 'Inactive'}</span></div><p className="mt-1 text-sm text-slate-500">{entry.email} · {entry.phone}</p><p className="mt-1 text-xs text-slate-400">{entry.branch ? `${entry.branch.code} - ${entry.branch.name}` : 'No branch assigned'}</p></div><button type="button" onClick={() => toggleStatus(entry)} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">{entry.is_active ? <ToggleOff fontSize="small" /> : <ToggleOn fontSize="small" />}{entry.is_active ? 'Deactivate' : 'Activate'}</button></article>)}
            {staff.length === 0 ? <p className="py-8 text-center text-sm text-slate-500">No staff records in your authorized scope.</p> : null}
          </section>
        </main>
      </div>
    </div>
  );
}

export default StaffManagement;
