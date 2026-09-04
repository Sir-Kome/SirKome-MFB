import { useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import api from '../services/api';

function ValidationMessage({ message }) {
  return message ? <p className="mt-1 text-xs text-rose-600">{message}</p> : null;
}

function Transfer() {
  const location = useLocation();
  const navigate = useNavigate();
  const storedUser = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
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
  const [receipt, setReceipt] = useState(null);
  const [showReceipt, setShowReceipt] = useState(false);
  const transferKeyRef = useRef(null);
  const submittingRef = useRef(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setError('');
  };

  const getTransferValidationMessage = (name, value) => {
    if (!value) return '';
    if (name === 'to_account' && value.trim().toUpperCase() === String(form.from_account || '').trim().toUpperCase()) {
      return 'Destination cannot be the same as your sending account.';
    }
    if (name === 'amount' && Number(value) <= 0) return 'Amount must be greater than zero.';
    if (name === 'pin' && !/^\d{4}$/.test(value)) return 'PIN must contain exactly 4 digits.';
    return '';
  };

  const doTransfer = async () => {
    if (submittingRef.current || !showPreview) {
      return;
    }

    submittingRef.current = true;
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const token = sessionStorage.getItem('sirkome_token');
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
        idempotency_key: transferKeyRef.current,
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
        const currentUser = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
        if (currentAccount && currentUser) {
          sessionStorage.setItem(
            'sirkome_user',
            JSON.stringify({ ...currentUser, balance: currentAccount.balance }),
          );
        }
      } catch (refreshError) {
        void refreshError;
      }

      setReceipt(response.data);
      setMessage(response.data.message);
      setForm((current) => ({ ...current, amount: '', to_account: '', pin: '' }));
      setShowPreview(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Transfer failed');
      transferKeyRef.current = null;
    } finally {
      submittingRef.current = false;
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
    if (String(form.from_account || '').trim().toUpperCase() === String(form.to_account || '').trim().toUpperCase()) {
      setError('You cannot transfer money to your own account.');
      return;
    }
    if (!/^[0-9]{4}$/.test(form.pin)) {
      setError('Enter a valid 4-digit PIN');
      return;
    }
    transferKeyRef.current = crypto.randomUUID
      ? crypto.randomUUID()
      : `transfer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setShowPreview(true);
  };

  const downloadReceiptPdf = () => {
    if (!receipt) return;
    const lines = [
      'SirKome Bank Transfer Receipt',
      `Receipt: ${receipt.receipt_id}`,
      `Date: ${receipt.date}`,
      `From account: ${receipt.from_account}`,
      `To account: ${receipt.to_account}`,
      `Amount: ${Number(receipt.amount).toFixed(2)}`,
      `Description: ${receipt.description}`,
      'Status: Successful',
    ];
    const escapePdfText = (value) => String(value).replace(/[^\x20-\x7E]/g, '?').replace(/[()\\]/g, '\\$&');
    const content = [
      'BT',
      '/F1 20 Tf',
      '50 760 Td',
      ...lines.flatMap((line, index) => [index === 0 ? `(${escapePdfText(line)}) Tj` : '0 -42 Td', index === 0 ? '' : `(${escapePdfText(line)}) Tj`]),
      'ET',
    ].filter(Boolean).join('\n');
    const objects = [
      '<< /Type /Catalog /Pages 2 0 R >>',
      '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
      '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
      '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
      `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    ];
    let pdf = '%PDF-1.4\n';
    const offsets = [0];
    objects.forEach((object, index) => {
      offsets.push(pdf.length);
      pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    offsets.slice(1).forEach((offset) => {
      pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
    const url = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${receipt.receipt_id || 'sirkome-transfer-receipt'}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const downloadReceiptImage = () => {
    if (!receipt) return;
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="900" height="620" viewBox="0 0 900 620">
        <rect width="900" height="620" fill="#f8fafc"/>
        <rect x="40" y="40" width="820" height="540" rx="24" fill="#ffffff" stroke="#cbd5e1"/>
        <text x="80" y="105" font-family="Arial" font-size="30" font-weight="700" fill="#0f172a">SirKome Bank Transfer Receipt</text>
        <text x="80" y="155" font-family="Arial" font-size="18" fill="#475569">Receipt: ${receipt.receipt_id}</text>
        <text x="80" y="205" font-family="Arial" font-size="20" fill="#334155">From account: ${receipt.from_account}</text>
        <text x="80" y="250" font-family="Arial" font-size="20" fill="#334155">To account: ${receipt.to_account}</text>
        <text x="80" y="295" font-family="Arial" font-size="20" fill="#334155">Amount: ${Number(receipt.amount).toFixed(2)}</text>
        <text x="80" y="340" font-family="Arial" font-size="20" fill="#334155">Description: ${receipt.description}</text>
        <text x="80" y="385" font-family="Arial" font-size="20" fill="#334155">Date: ${receipt.date}</text>
        <text x="80" y="465" font-family="Arial" font-size="24" font-weight="700" fill="#047857">Successful</text>
      </svg>`;
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${receipt.receipt_id || 'sirkome-transfer-receipt'}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const startAnotherTransfer = () => {
    setReceipt(null);
    setShowReceipt(false);
    setMessage('');
    setError('');
    transferKeyRef.current = null;
  };

  if (receipt) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-10 text-slate-800 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl rounded-[32px] border border-emerald-100 bg-white p-8 shadow-2xl sm:p-10">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-3xl text-emerald-700">✓</div>
            <p className="mt-5 text-sm font-medium uppercase tracking-[0.3em] text-emerald-600">Transfer successful</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Money sent successfully</h1>
            <p className="mt-3 text-slate-600">{Number(receipt.amount).toFixed(2)} was sent to {receipt.to_account}.</p>
          </div>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm">
            <div className="flex justify-between gap-4"><span className="font-medium text-slate-500">Receipt</span><span>{receipt.receipt_id}</span></div>
            <div className="mt-3 flex justify-between gap-4"><span className="font-medium text-slate-500">Date</span><span>{receipt.date}</span></div>
            <div className="mt-3 flex justify-between gap-4"><span className="font-medium text-slate-500">Description</span><span>{receipt.description}</span></div>
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={() => setShowReceipt(true)} className="flex-1 rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 font-semibold text-cyan-800">View receipt</button>
            <button type="button" onClick={downloadReceiptPdf} className="flex-1 rounded-2xl bg-slate-900 px-4 py-3 font-semibold text-white">Download PDF receipt</button>
            <button type="button" onClick={downloadReceiptImage} className="flex-1 rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700">Download image receipt</button>
          </div>
          <div className="mt-4 flex justify-center gap-4 text-sm font-medium">
            <button type="button" onClick={startAnotherTransfer} className="text-cyan-700">Make another transfer</button>
            <a href="/dashboard" className="text-cyan-700">Back to dashboard</a>
          </div>
        </div>
        {showReceipt ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-xl font-semibold text-slate-900">Transfer receipt</h2>
                <button type="button" onClick={() => setShowReceipt(false)} className="text-sm font-medium text-slate-500">Close</button>
              </div>
              <div className="mt-5 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
                <div className="flex justify-between gap-4"><span className="text-slate-500">Status</span><span className="font-semibold text-emerald-700">Successful</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">Amount</span><span>{Number(receipt.amount).toFixed(2)}</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">From</span><span>{receipt.from_account}</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">To</span><span>{receipt.to_account}</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">Date</span><span>{receipt.date}</span></div>
              </div>
              <div className="mt-5 flex gap-3">
                <button type="button" onClick={downloadReceiptPdf} className="flex-1 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white">Download PDF</button>
                <button type="button" onClick={downloadReceiptImage} className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700">Download image</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

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
            <ValidationMessage message={getTransferValidationMessage('to_account', form.to_account)} />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Amount</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
              name="amount"
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0"
              placeholder="250"
              value={form.amount}
              onChange={handleChange}
              required
            />
            <ValidationMessage message={getTransferValidationMessage('amount', form.amount)} />
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
            <ValidationMessage message={getTransferValidationMessage('pin', form.pin)} />
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
                <button type="button" onClick={doTransfer} disabled={loading} className="flex-1 rounded-2xl bg-emerald-600 px-4 py-3 text-white disabled:cursor-not-allowed disabled:opacity-70">{loading ? 'Sending...' : 'Confirm and send'}</button>
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