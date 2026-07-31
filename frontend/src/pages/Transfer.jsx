import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import api from '../services/api';

function Transfer() {
  const location = useLocation();
  const navigate = useNavigate();
  const storedUser = JSON.parse(localStorage.getItem('sirkome_user') || 'null');
  const [form, setForm] = useState(() => ({
    from_account: location.state?.fromAccount || storedUser?.account_number || '',
    to_account: '',
    amount: '',
    description: 'Demo transfer',
    pin: '',
  }));
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const doTransfer = async () => {
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const token = localStorage.getItem('sirkome_token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await api.post('/transfer', {
        from_account: form.from_account,
        to_account: form.to_account,
        amount: Number(form.amount),
        description: form.description,
        pin: form.pin,
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });

      try {
        const accountsResponse = await api.get('/accounts', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const currentAccount = accountsResponse.data.find(
          (account) => account.account_number === form.from_account,
        ) || accountsResponse.data[0];
        const currentUser = JSON.parse(localStorage.getItem('sirkome_user') || 'null');
        if (currentAccount && currentUser) {
          localStorage.setItem(
            'sirkome_user',
            JSON.stringify({ ...currentUser, balance: currentAccount.balance }),
          );
        }
      } catch (refreshError) {
        void refreshError;
      }

      setMessage(response.data.message);
      setForm((current) => ({ ...current, amount: '', to_account: '', pin: '' }));
      setShowPreview(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Transfer failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = (event) => {
    event.preventDefault();
    setError('');
    if (!form.to_account || !form.amount || Number(form.amount) <= 0) {
      setError('Please enter a valid destination account and a positive amount.');
      return;
    }
    if (!/^[0-9]{4}$/.test(form.pin)) {
      setError('Enter a valid 4-digit PIN');
      return;
    }
    setShowPreview(true);
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-6 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl rounded-[32px] border border-slate-200 bg-white p-8 shadow-2xl">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-600">Transfer funds</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Send money securely</h1>
          </div>
          <a href="/dashboard" className="text-sm font-medium text-cyan-600">Back to dashboard</a>
        </div>

        <form onSubmit={handlePreview} className="mt-8 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">From account</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="from_account"
              value={form.from_account}
              onChange={handleChange}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">To account</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="to_account"
              placeholder="SK-123456"
              value={form.to_account}
              onChange={handleChange}
              required
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Amount</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="250"
              value={form.amount}
              onChange={handleChange}
              required
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Description</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="description"
              value={form.description}
              onChange={handleChange}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">4-digit transfer PIN</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="pin"
              type="password"
              inputMode="numeric"
              maxLength={4}
              pattern="\d{4}"
              value={form.pin}
              onChange={handleChange}
              required
            />
          </label>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? 'Processing...' : 'Preview transfer'}
          </button>
        </form>

        {showPreview ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="mx-auto w-full max-w-md rounded-2xl bg-white p-6 shadow-lg">
              <h3 className="text-lg font-semibold">Confirm transfer</h3>
              <p className="mt-3 text-sm text-slate-700">Please review before submitting.</p>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between"><span className="font-medium">From</span><span>{form.from_account}</span></div>
                <div className="flex justify-between"><span className="font-medium">To</span><span>{form.to_account}</span></div>
                <div className="flex justify-between"><span className="font-medium">Amount</span><span>{form.amount}</span></div>
                <div className="flex justify-between"><span className="font-medium">Description</span><span>{form.description}</span></div>
              </div>
              <div className="mt-6 flex gap-3">
                <button onClick={() => doTransfer()} className="flex-1 rounded-2xl bg-emerald-600 px-4 py-3 text-white">Confirm and send</button>
                <button onClick={() => setShowPreview(false)} className="flex-1 rounded-2xl border border-slate-200 px-4 py-3">Cancel</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default Transfer;