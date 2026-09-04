import ContentCopy from '@mui/icons-material/ContentCopy';
import { useState } from 'react';

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const input = document.createElement('textarea');
  input.value = value;
  input.setAttribute('readonly', '');
  input.style.position = 'fixed';
  input.style.opacity = '0';
  document.body.appendChild(input);
  input.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(input);
  if (!copied) throw new Error('Clipboard copy failed');
}

function AccountNumberCopy({ accountNumber, className = '' }) {
  const [status, setStatus] = useState('');

  const handleCopy = async () => {
    if (!accountNumber) return;
    try {
      await copyText(accountNumber);
      setStatus('Copied!');
      window.setTimeout(() => setStatus(''), 1500);
    } catch {
      setStatus('Copy failed');
      window.setTimeout(() => setStatus(''), 2000);
    }
  };

  return (
    <span className={`inline-flex items-center gap-1 ${className}`}>
      <button
        type="button"
        onClick={handleCopy}
        disabled={!accountNumber}
        aria-label="Copy account number"
        title="Copy account number"
        className="inline-flex items-center gap-1 rounded-xl p-1 text-slate-500 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ContentCopy fontSize="small" />
        <span className="sr-only">Copy</span>
      </button>
      {status ? <span className={`text-[10px] font-semibold uppercase tracking-wide ${status === 'Copied!' ? 'text-emerald-600' : 'text-rose-600'}`}>{status}</span> : null}
    </span>
  );
}

export default AccountNumberCopy;
