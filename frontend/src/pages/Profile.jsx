import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AccountCircle, Verified } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => JSON.parse(sessionStorage.getItem('sirkome_user') || 'null'));
  const [form, setForm] = useState({ name: '', phone: '', email: '', date_of_birth: '', gender: '' });
  const [upgrade, setUpgrade] = useState({ nin: '', bvn: '', address: '', proof_of_address_date: '', file: null });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem('sirkome_token');
    if (!token) {
      navigate('/login');
      return;
    }
    api.get('/profile', { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        setUser(response.data);
        setForm({ name: response.data.name || '', phone: response.data.phone || '', email: response.data.email || '', date_of_birth: response.data.date_of_birth || '', gender: response.data.gender || '' });
        sessionStorage.setItem('sirkome_user', JSON.stringify(response.data));
      })
      .catch(() => navigate('/login'));
  }, [navigate]);

  const updateContact = async (event) => {
    event.preventDefault();
    setSaving(true); setError(''); setMessage('');
    try {
      const token = sessionStorage.getItem('sirkome_token');
      await api.post('/profile/update', form, { headers: { Authorization: `Bearer ${token}` } });
      const response = await api.get('/profile', { headers: { Authorization: `Bearer ${token}` } });
      setUser(response.data); sessionStorage.setItem('sirkome_user', JSON.stringify(response.data)); setMessage('Profile details updated.');
    } catch (err) { setError(err.response?.data?.detail || 'Unable to update your profile.'); } finally { setSaving(false); }
  };

  const encodeFile = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

  const upgradeTier = async (event) => {
    event.preventDefault();
    setSaving(true); setError(''); setMessage('');
    try {
      const token = sessionStorage.getItem('sirkome_token');
      const data = { nin: upgrade.nin || undefined, bvn: upgrade.bvn || undefined, address: upgrade.address || undefined, proof_of_address_date: upgrade.proof_of_address_date || undefined };
      if (upgrade.file) { data.proof_of_address_filename = upgrade.file.name; data.proof_of_address_data = await encodeFile(upgrade.file); }
      const response = await api.post('/profile/upgrade', data, { headers: { Authorization: `Bearer ${token}` } });
      setUser(response.data.user); sessionStorage.setItem('sirkome_user', JSON.stringify(response.data.user)); setMessage(response.data.message); setUpgrade((current) => ({ ...current, nin: '', bvn: '', address: '', proof_of_address_date: '', file: null }));
    } catch (err) { setError(err.response?.data?.detail || 'Unable to upgrade your profile.'); } finally { setSaving(false); }
  };

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_35%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row"><Sidebar /><main className="flex-1 space-y-4"><Navbar user={user} />
        <div className="grid gap-4 2xl:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-[28px] border border-slate-200/70 bg-white/85 p-6 shadow-lg backdrop-blur">
            <div className="flex items-center gap-3"><AccountCircle className="text-cyan-600" sx={{ fontSize: 44 }} /><div><p className="text-sm uppercase tracking-wide text-cyan-600">Customer profile</p><h1 className="text-2xl font-semibold text-slate-950">Your details</h1></div></div>
            <div className="mt-6 rounded-2xl bg-slate-950 p-5 text-white"><div className="flex items-center justify-between"><span className="text-sm text-slate-300">Verification status</span><Verified className="text-emerald-300" /></div><p className="mt-2 text-3xl font-semibold">{user.tier}</p><p className="mt-1 text-sm text-slate-300">Daily transfer limit: NGN {Number(user.daily_transfer_limit || 0).toLocaleString()}</p></div>
            <form onSubmit={updateContact} className="mt-6 space-y-4"><label className="block text-sm font-medium">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">Phone<input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-medium">Date of birth<input type="date" max={new Date().toISOString().split('T')[0]} value={form.date_of_birth} onChange={(event) => setForm({ ...form, date_of_birth: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">Gender<select value={form.gender} onChange={(event) => setForm({ ...form, gender: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"><option value="">Select gender</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option><option value="prefer_not_to_say">Prefer not to say</option></select></label></div><button disabled={saving} className="w-full rounded-2xl bg-cyan-600 px-4 py-3 font-semibold text-white hover:bg-cyan-700 disabled:opacity-50">Save profile</button></form>
          </section>
          <section className="rounded-[28px] border border-slate-200/70 bg-white/85 p-6 shadow-lg backdrop-blur"><p className="text-sm uppercase tracking-wide text-rose-600">Account upgrade</p><h2 className="mt-1 text-2xl font-semibold text-slate-950">Increase your limits</h2><p className="mt-2 text-sm text-slate-500">Tier 2 requires both NIN and BVN. Tier 3 additionally requires a recent proof of address verified with Google Maps.</p>
            <form onSubmit={upgradeTier} className="mt-6 space-y-4"><label className="block text-sm font-medium">NIN (optional if already supplied)<input inputMode="numeric" maxLength={11} value={upgrade.nin} onChange={(event) => setUpgrade({ ...upgrade, nin: event.target.value.replace(/\D/g, '').slice(0, 11) })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">BVN (optional if already supplied)<input inputMode="numeric" maxLength={11} value={upgrade.bvn} onChange={(event) => setUpgrade({ ...upgrade, bvn: event.target.value.replace(/\D/g, '').slice(0, 11) })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">Full residential address<input value={upgrade.address} onChange={(event) => setUpgrade({ ...upgrade, address: event.target.value })} placeholder="Used for Google Maps verification" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-medium">Document date<input type="date" value={upgrade.proof_of_address_date} onChange={(event) => setUpgrade({ ...upgrade, proof_of_address_date: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" /></label><label className="block text-sm font-medium">Proof document<input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(event) => setUpgrade({ ...upgrade, file: event.target.files?.[0] || null })} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm" /></label></div><button disabled={saving} className="w-full rounded-2xl bg-rose-600 px-4 py-3 font-semibold text-white hover:bg-rose-700 disabled:opacity-50">Submit upgrade</button></form>
            {message ? <p className="mt-4 text-sm font-medium text-emerald-700">{message}</p> : null}{error ? <p className="mt-4 text-sm font-medium text-rose-600">{error}</p> : null}
          </section>
        </div>
      </main></div>
    </div>
  );
}

export default Profile;
