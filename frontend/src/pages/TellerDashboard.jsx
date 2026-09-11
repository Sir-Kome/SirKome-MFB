import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { AccountBalance, Search, SwapHoriz } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function TellerDashboard() {
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  const token = sessionStorage.getItem('sirkome_token');
  const [query, setQuery] = useState('');
  const [customers, setCustomers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [operation, setOperation] = useState('DEPOSIT');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token || user?.role !== 'TELLER') return;
    api.get('/teller/transactions', { headers: { Authorization: `Bearer ${token}` } }).then((response) => setTransactions(response.data || [])).catch(() => {});
  }, [token, user?.role]);

  if (!user || !token) return <Navigate to="/staff/login" replace />;
  if (user.role !== 'TELLER') return <Navigate to="/staff/dashboard" replace />;

  const search = async (event) => {
    event.preventDefault();
    setMessage('');
    try {
      const response = await api.get('/teller/customers', { params: { query }, headers: { Authorization: `Bearer ${token}` } });
      setCustomers(response.data || []);
      setSelected(null);
      if (!response.data?.length) setMessage('No customer found in your authorized branch.');
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to search customers.');
    }
  };

  const submitOperation = async (event) => {
    event.preventDefault();
    if (!selected) { setMessage('Select a customer account first.'); return; }
    setBusy(true);
    setMessage('');
    try {
      const endpoint = operation === 'DEPOSIT' ? '/teller/deposits' : '/teller/withdrawals';
      const response = await api.post(endpoint, { account_number: selected.account_number, amount, description }, { headers: { Authorization: `Bearer ${token}` } });
      setMessage(`${operation} completed: ${response.data.transaction_reference}`);
      setSelected({ ...selected, balance: operation === 'DEPOSIT' ? selected.balance + Number(amount) : selected.balance - Number(amount) });
      setAmount('');
      setDescription('');
      const transactionsResponse = await api.get('/teller/transactions', { headers: { Authorization: `Bearer ${token}` } });
      setTransactions(transactionsResponse.data || []);
    } catch (error) {
      setMessage(error.response?.data?.detail || `Unable to process ${operation.toLowerCase()}.`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.16),_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_100%)] px-4 py-5 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row">
        <Sidebar />
        <main className="flex-1 space-y-4">
          <Navbar user={user} />
          <section className="rounded-[28px] bg-slate-950 p-6 text-white shadow-xl"><p className="text-sm font-medium uppercase tracking-[0.18em] text-cyan-300">Teller operations</p><h1 className="mt-2 text-3xl font-semibold">Customer service desk</h1><p className="mt-2 max-w-xl text-sm text-slate-300">Look up an authorized customer, then process a deposit or withdrawal securely.</p></section>
          <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
            <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg"><div className="flex items-center gap-3"><Search className="text-cyan-600" /><div><p className="text-sm text-slate-500">Customer lookup</p><h2 className="text-lg font-semibold text-slate-900">Find an account</h2></div></div><form onSubmit={search} className="mt-5 flex gap-2"><input required minLength="2" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Account number or name" className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" /><button type="submit" className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Search</button></form><div className="mt-4 space-y-2">{customers.map((customer) => <button key={customer.user_id} type="button" onClick={() => setSelected(customer)} className={`w-full rounded-2xl border p-3 text-left ${selected?.user_id === customer.user_id ? 'border-cyan-500 bg-cyan-50' : 'border-slate-200 bg-slate-50'}`}><p className="font-semibold text-slate-900">{customer.name}</p><p className="text-sm text-slate-500">{customer.account_number} · ₦{Number(customer.balance).toFixed(2)}</p></button>)}</div></section>
            <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg"><div className="flex items-center gap-3"><AccountBalance className="text-cyan-600" /><div><p className="text-sm text-slate-500">Financial operation</p><h2 className="text-lg font-semibold text-slate-900">{selected ? selected.name : 'Select an account'}</h2></div></div>{selected ? <><div className="mt-5 rounded-2xl bg-slate-950 p-4 text-white"><p className="text-sm text-slate-300">Current balance</p><p className="mt-1 text-3xl font-semibold">₦{Number(selected.balance).toFixed(2)}</p><p className="mt-1 text-xs text-slate-400">{selected.account_number}</p></div><form onSubmit={submitOperation} className="mt-5 space-y-3"><div className="grid grid-cols-2 gap-2"><button type="button" onClick={() => setOperation('DEPOSIT')} className={`rounded-xl px-3 py-2 text-sm font-semibold ${operation === 'DEPOSIT' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'}`}>Deposit</button><button type="button" onClick={() => setOperation('WITHDRAWAL')} className={`rounded-xl px-3 py-2 text-sm font-semibold ${operation === 'WITHDRAWAL' ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-700'}`}>Withdrawal</button></div><input required min="0.01" step="0.01" type="number" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Amount" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" /><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description (optional)" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" /><button disabled={busy} type="submit" className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"><SwapHoriz fontSize="small" />{busy ? 'Processing...' : `Process ${operation.toLowerCase()}`}</button></form></> : <p className="mt-6 rounded-2xl bg-slate-50 p-5 text-sm text-slate-500">Search for a customer to begin.</p>}{message ? <p className="mt-4 text-sm font-medium text-slate-700">{message}</p> : null}</section>
          </div>
          <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-lg"><h2 className="text-lg font-semibold text-slate-900">Recent teller transactions</h2><div className="mt-4 space-y-2">{transactions.slice(0, 10).map((item) => <div key={item.transaction_reference} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-slate-50 p-3 text-sm"><div><p className="font-semibold text-slate-800">{item.type} · {item.transaction_reference}</p><p className="text-slate-500">{item.account_number} · {item.description}</p></div><span className="font-semibold text-slate-700">₦{Number(item.amount).toFixed(2)}</span></div>)}{transactions.length === 0 ? <p className="py-5 text-sm text-slate-500">No teller transactions yet.</p> : null}</div></section>
        </main>
      </div>
    </div>
  );
}

export default TellerDashboard;
