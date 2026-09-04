import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import api from '../services/api';

const validateEmailAddress = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

function ValidationMessage({ message }) {
  return message ? <p className="mt-1 text-xs text-rose-600">{message}</p> : null;
}

function Login() {
  const navigate = useNavigate();
  const [storyIndex, setStoryIndex] = useState(0);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem('sirkome_token')) {
      navigate('/dashboard');
    }
  }, [navigate]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStoryIndex((current) => (current + 1) % 3);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    if (!email.trim() || !validateEmailAddress(email)) {
      setError('Please enter a valid email address.');
      setLoading(false);
      return;
    }

    if (!password.trim()) {
      setError('Password is required.');
      setLoading(false);
      return;
    }

    try {
      const response = await api.post('/auth/login', { email, password });
      const { token, user } = response.data;
      sessionStorage.setItem('sirkome_token', token);
      sessionStorage.setItem('sirkome_user', JSON.stringify(user));
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = detail || (err.message ? `Unable to reach the bank server: ${err.message}` : 'Unable to sign in right now.');
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-3 py-4 text-slate-800 sm:px-6 sm:py-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-6xl flex-col overflow-hidden rounded-[28px] border border-white/70 bg-white/80 shadow-2xl backdrop-blur sm:min-h-[calc(100vh-3rem)] sm:rounded-[32px] lg:flex-row">
        <div className="relative hidden min-h-[520px] flex-1 flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-8 text-white lg:flex lg:min-h-0 lg:p-14">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 font-semibold">
              SB
            </div>
            <div>
              <p className="text-sm text-slate-400">Secure banking</p>
              <p className="text-lg font-semibold">SirKome Bank</p>
            </div>
          </div>

          <div className="relative flex flex-1 items-center py-10">
            {storyIndex === 0 ? (
              <div key="banking" className="login-story login-story-enter">
                <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Your money, your momentum</p>
                <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Banking that feels effortless.</h1>
                <p className="mt-4 max-w-md text-base text-slate-300 sm:text-lg">Track your money, move funds instantly, and stay on top of your goals from one beautiful dashboard.</p>
              </div>
            ) : null}
            {storyIndex === 1 ? (
              <div key="creator" className="login-story login-story-enter">
                <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Built with intention</p>
                <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Meet the creator.</h1>
                <p className="mt-4 max-w-md text-base leading-7 text-slate-300 sm:text-lg">I’m Kome Isioro, the creator behind SirKome Bank. I designed this experience to make everyday banking feel clear, confident, and human.</p>
              </div>
            ) : null}
            {storyIndex === 2 ? (
              <div key="portrait" className="login-story login-story-enter flex w-full items-center gap-5">
                <img src="/creator.jpeg" alt="Kome Isioro, creator of SirKome Bank" className="h-32 w-24 shrink-0 rounded-2xl object-cover object-top shadow-2xl ring-1 ring-white/20 sm:h-44 sm:w-32" />
                <div><p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Creator profile</p><h1 className="mt-3 text-2xl font-semibold sm:text-3xl">Hi, I’m Kome.</h1><p className="mt-3 text-sm leading-6 text-slate-300 sm:text-base">Thanks for being here. Welcome to a bank built for thoughtful progress.</p></div>
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-2" aria-label="Login introduction slides">
            {[0, 1, 2].map((index) => (
              <button key={index} type="button" aria-label={`Show introduction slide ${index + 1}`} onClick={() => setStoryIndex(index)} className={`h-1.5 rounded-full transition-all ${storyIndex === index ? 'w-10 bg-cyan-400' : 'w-5 bg-white/30 hover:bg-white/60'}`} />
            ))}
          </div>

        </div>

        <div className="flex flex-1 items-center justify-center px-2 py-8 sm:p-8 lg:p-10">
          <form onSubmit={handleLogin} className="w-full max-w-md rounded-[24px] border border-slate-200 bg-white p-5 shadow-lg sm:rounded-[28px] sm:p-8">
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 font-semibold text-white">SB</div>
              <div><p className="text-xs uppercase tracking-[0.2em] text-slate-500">Secure banking</p><p className="font-semibold text-slate-900">SirKome Bank</p></div>
            </div>
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-600">Welcome back</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">Sign in to your account</h2>

            <label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="email">
              Enter Email <span className="text-rose-500">*</span>
            </label>
            <input
              id="email"
              className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition focus:border-cyan-500 focus:bg-white"
              placeholder="demo@sirkome.com"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <ValidationMessage message={email && !validateEmailAddress(email) ? 'Invalid email. Include @ and a domain such as .com.' : ''} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="password">
              Enter Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-2">
              <input
                id="password"
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12 outline-none transition focus:border-cyan-500 focus:bg-white"
                placeholder="Enter your password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((current) => !current)}
                className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-700"
              >
                {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            <ValidationMessage message={password && password.length < 8 ? 'Password must be at least 8 characters.' : ''} />

            {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>

            <p className="mt-4 text-center text-sm text-slate-500">
              New here? <a href="/register" className="font-medium text-cyan-600">Create an account</a>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;