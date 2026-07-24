import { CreditCard, Visibility, VisibilityOff } from '@mui/icons-material';
import { useState } from 'react';

function BalanceCard({ balance, accountNumber, userName, onSend }) {
  const [showAccountNumber, setShowAccountNumber] = useState(false);
  const [showBalance, setShowBalance] = useState(false);
  const maskedAccountNumber = accountNumber ? `•••• ${accountNumber.slice(-4)}` : '••••';

  return (
    <section className="rounded-[32px] bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-6 text-white shadow-2xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">Available balance</p>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-4xl font-semibold">{showBalance ? `$${Number(balance || 0).toFixed(2)}` : '••••••'}</p>
            <button
              type="button"
              aria-label={showBalance ? 'Hide balance' : 'Show balance'}
              title={showBalance ? 'Hide balance' : 'Show balance'}
              onClick={() => setShowBalance((current) => !current)}
              className="rounded-xl p-2 text-slate-300 transition hover:bg-white/10 hover:text-white"
            >
              {showBalance ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
            </button>
          </div>
        </div>
        <div className="rounded-2xl bg-white/10 p-3">
          <CreditCard />
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div className="text-sm font-medium text-slate-300">
          {userName || 'Cardholder'}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-2xl border border-white/20 bg-white/10 px-3 py-1 text-sm text-slate-200">
            <span>{showAccountNumber ? accountNumber : maskedAccountNumber}</span>
            <button
              type="button"
              aria-label={showAccountNumber ? 'Hide account number' : 'Show account number'}
              title={showAccountNumber ? 'Hide account number' : 'Show account number'}
              onClick={() => setShowAccountNumber((current) => !current)}
              className="rounded-xl p-2 transition hover:bg-white/10"
            >
              {showAccountNumber ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
            </button>
          </div>
          <button
            type="button"
            onClick={onSend}
            className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-3 text-sm font-medium text-white shadow-lg"
          >
            <span>↗</span>
            Send
          </button>
          <button className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-violet-500 to-fuchsia-600 px-4 py-3 text-sm font-medium text-white shadow-lg">
            <span>↓</span>
            Top up
          </button>
        </div>
      </div>
    </section>
  );
}

export default BalanceCard;