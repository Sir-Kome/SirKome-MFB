import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import api from '../services/api';

const getSavedDraftEmail = () => {
  const draft = JSON.parse(sessionStorage.getItem('sirkome_registration_draft') || 'null');
  return draft?.email || '';
};

function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const [email] = useState(location.state?.email || getSavedDraftEmail());
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!email) {
      navigate('/register', { replace: true });
    }
  }, [email, navigate]);

  const handleVerify = async (event) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError('Enter the 6-digit verification code.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await api.post('/auth/verify-email', { email, code });
      navigate('/register', {
        replace: true,
        state: { emailVerified: true },
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'The verification code is invalid or expired.');
    } finally {
      setLoading(false);
    }
  };

  const resendCode = async () => {
    setResending(true);
    setError('');
    setMessage('');
    try {
      await api.post('/auth/send-verification', { email });
      setMessage('A new verification code was sent. It expires in 15 minutes.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to resend the verification code.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-6 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col overflow-hidden rounded-[32px] border border-white/70 bg-white/80 shadow-2xl backdrop-blur lg:flex-row">
        <div className="flex flex-1 flex-col justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-8 text-white sm:p-10 lg:p-14">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Email verification</p>
          <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Confirm your email before opening an account</h1>
          <p className="mt-4 max-w-md text-base text-slate-300">Enter the six-digit code sent to your email address. The code is valid for 15 minutes.</p>
        </div>

        <div className="flex flex-1 items-center justify-center p-6 sm:p-8 lg:p-10">
          <form onSubmit={handleVerify} className="w-full max-w-md rounded-[28px] border border-slate-200 bg-white p-6 shadow-lg sm:p-8">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-600">Verify email</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">Enter your code</h2>
            <p className="mt-3 text-sm text-slate-500">Code sent to <span className="font-medium text-slate-700">{email}</span></p>

            <label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="verification_code">6-digit verification code</label>
            <input
              id="verification_code"
              className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-center text-xl tracking-[0.4em] outline-none focus:border-cyan-500 focus:bg-white"
              inputMode="numeric"
              maxLength={6}
              autoComplete="one-time-code"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              autoFocus
              required
            />
            {code && !/^\d{6}$/.test(code) ? <p className="mt-1 text-xs text-rose-600">Verification code must contain exactly 6 digits.</p> : null}

            {message ? <p className="mt-4 text-sm text-emerald-600">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

            <button type="submit" disabled={loading} className="mt-6 w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-70">
              {loading ? 'Verifying...' : 'Verify email'}
            </button>
            <button type="button" onClick={resendCode} disabled={resending} className="mt-3 w-full rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-70">
              {resending ? 'Resending...' : 'Resend code'}
            </button>
            <button type="button" onClick={() => navigate('/register')} className="mt-4 w-full text-sm font-medium text-cyan-700">Back to registration</button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default VerifyEmail;
