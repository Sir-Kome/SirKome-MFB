import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AccountBalance, Send, Visibility, VisibilityOff } from '@mui/icons-material';

import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import api from '../services/api';

function Accounts() {
	const navigate = useNavigate();
	const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
	const userAccountNumber = user?.account_number;
	const [accounts, setAccounts] = useState([]);
	const [visibleFields, setVisibleFields] = useState({});

	const toggleField = (accountNumber, field) => {
		setVisibleFields((current) => ({
			...current,
			[accountNumber]: { ...current[accountNumber], [field]: !current[accountNumber]?.[field] },
		}));
	};

	useEffect(() => {
		const token = sessionStorage.getItem('sirkome_token');
		if (!token || !userAccountNumber) {
			navigate('/login');
			return;
		}

		api.get('/accounts', { headers: { Authorization: `Bearer ${token}` } })
			.then((response) => setAccounts(response.data))
			.catch(() => navigate('/login'));
	}, [navigate, userAccountNumber]);

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
						<p className="text-sm text-slate-500">Your accounts</p>
						<h1 className="mt-1 text-2xl font-semibold text-slate-900">Manage every account</h1>
						<div className="mt-6 grid gap-4 md:grid-cols-2">
							{accounts.map((account) => (
								<article key={account.account_number} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
									<div className="flex items-start justify-between gap-4">
										<div className="rounded-2xl bg-slate-900 p-3 text-white">
											<AccountBalance />
										</div>
										<span className="text-sm text-slate-500">{account.type}</span>
									</div>
									<div className="mt-5 flex items-center gap-2 text-sm text-slate-500">
										<span>{visibleFields[account.account_number]?.account ? account.account_number : `•••• ${account.account_number.slice(-4)}`}</span>
										<button
											type="button"
											aria-label={visibleFields[account.account_number]?.account ? 'Hide account number' : 'Show account number'}
											title={visibleFields[account.account_number]?.account ? 'Hide account number' : 'Show account number'}
											onClick={() => toggleField(account.account_number, 'account')}
											className="rounded-xl p-1 transition hover:bg-slate-200"
										>
											{visibleFields[account.account_number]?.account ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
										</button>
									</div>
									<div className="mt-1 flex items-center gap-2">
										<p className="text-3xl font-semibold text-slate-900">
											{visibleFields[account.account_number]?.balance ? `${account.currency} ${Number(account.balance || 0).toFixed(2)}` : '••••••'}
										</p>
										<button
											type="button"
											aria-label={visibleFields[account.account_number]?.balance ? 'Hide balance' : 'Show balance'}
											title={visibleFields[account.account_number]?.balance ? 'Hide balance' : 'Show balance'}
											onClick={() => toggleField(account.account_number, 'balance')}
											className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-200"
										>
											{visibleFields[account.account_number]?.balance ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
										</button>
									</div>
									<button
										type="button"
										onClick={() => navigate('/transfer', { state: { fromAccount: account.account_number } })}
										className="mt-5 flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-3 text-sm font-medium text-white shadow-lg"
									>
										<Send fontSize="small" />
										Transfer from this account
									</button>
								</article>
							))}
						</div>
					</section>
				</main>
			</div>
		</div>
	);
}

export default Accounts;
