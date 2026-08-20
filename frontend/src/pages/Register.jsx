import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import api from '../services/api';

const validateEmailAddress = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
const validateName = (value) => /^[A-Za-z\s'-]+$/.test(value.trim());
const validateNigerianPhone = (value) => /^(\+234|234|0)\d{10}$/.test(value.replace(/\s+/g, ''));
const validatePassword = (value) => /^(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,}$/.test(value);
const validateIdentity = (value) => /^\d{11}$/.test(value);

function ValidationMessage({ message }) {
  return message ? <p className="mt-1 text-xs text-rose-600">{message}</p> : null;
}

const getValidationMessage = (name, value, form) => {
  if (!value) return '';
  if (name === 'first_name' || name === 'last_name' || name === 'middle_name') {
    return validateName(value) ? '' : 'Use letters, spaces, apostrophes, or hyphens only.';
  }
  if (name === 'email') return validateEmailAddress(value) ? '' : 'Invalid email. Include @ and a domain such as .com.';
  if (name === 'phone') return validateNigerianPhone(value) ? '' : 'Enter a valid Nigerian mobile number.';
  if (name === 'nin' || name === 'bvn') return validateIdentity(value) ? '' : 'Must contain exactly 11 digits.';
  if (name === 'password') return validatePassword(value) ? '' : 'Use 8+ characters, one number, and one special character.';
  if (name === 'password_confirmation') return value === form.password ? '' : 'Passwords do not match.';
  if (name === 'pin' || name === 'pin_confirmation') {
    if (!/^\d{4}$/.test(value)) return 'PIN must contain exactly 4 digits.';
    return name === 'pin_confirmation' && value !== form.pin ? 'PINs do not match.' : '';
  }
  return '';
};

function Register() {
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState(() => {
    const savedDraft = sessionStorage.getItem('sirkome_registration_draft');
    return savedDraft ? JSON.parse(savedDraft) : {
      first_name: '',
      last_name: '',
      middle_name: '',
      email: '',
      password: '',
      password_confirmation: '',
      phone: '',
      nin: '',
      bvn: '',
      pin: '',
      pin_confirmation: '',
    };
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPin, setShowPin] = useState(false);
  const [showPinConfirmation, setShowPinConfirmation] = useState(false);
  const [emailVerified] = useState(Boolean(location.state?.emailVerified));
  const [verificationLoading, setVerificationLoading] = useState(false);

  useEffect(() => {
    if (location.state?.emailVerified) {
      sessionStorage.removeItem('sirkome_registration_draft');
    }
  }, [location.state]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    const sanitizedValue = name === 'nin' || name === 'bvn'
      ? value.replace(/\D/g, '').slice(0, 11)
      : name === 'pin' || name === 'pin_confirmation'
        ? value.replace(/\D/g, '').slice(0, 4)
        : name === 'phone'
          ? value.replace(/[^\d+\s]/g, '').slice(0, 20)
          : name === 'first_name' || name === 'last_name' || name === 'middle_name'
            ? value.replace(/[^A-Za-z\s'-]/g, '')
            : value;
    setForm((current) => ({ ...current, [name]: sanitizedValue }));
  };

  const validateIdentity = (value) => /^\d{11}$/.test(value);
  const validateNigerianPhone = (value) => /^(\+234|234|0)\d{10}$/.test(value.replace(/\s+/g, ''));
  const validateName = (value) => /^[A-Za-z][A-Za-z\s'-]*$/.test(value.trim());

  const sendVerificationCode = async () => {
    if (!form.first_name || !form.last_name || !validateName(form.first_name) || !validateName(form.last_name)) {
      setError('First name and last name are required and must contain only letters, spaces, apostrophes, or hyphens.');
      return;
    }
    if (form.middle_name && !validateName(form.middle_name)) {
      setError('Middle name must contain only letters, spaces, apostrophes, or hyphens.');
      return;
    }
    if (!validateEmailAddress(form.email)) {
      setError('Please enter a valid email address before requesting a verification code.');
      return;
    }
    if (!validateNigerianPhone(form.phone) || !validateIdentity(form.nin) || !validateIdentity(form.bvn)) {
      setError('Enter a valid Nigerian phone number, 11-digit NIN, and 11-digit BVN first.');
      return;
    }
    if (!/^\d{4}$/.test(form.pin) || form.pin !== form.pin_confirmation) {
      setError('PIN must be 4 digits and both PIN fields must match.');
      return;
    }
    if (!validatePassword(form.password) || form.password !== form.password_confirmation) {
      setError('Password must be at least 8 characters, include a number and special character, and match confirmation.');
      return;
    }

    setVerificationLoading(true);
    setError('');

    try {
      await api.post('/auth/send-verification', { email: form.email });
      sessionStorage.setItem('sirkome_registration_draft', JSON.stringify(form));
      navigate('/verify-email', {
        state: { email: form.email },
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to send verification code.');
    } finally {
      setVerificationLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    const fullName = `${form.first_name || ''} ${form.last_name || ''}`.trim();
    if (!form.first_name || !form.last_name || !validateName(form.first_name) || !validateName(form.last_name)) {
      setError('First name and last name are required and must contain only letters, spaces, apostrophes, or hyphens.');
      setLoading(false);
      return;
    }

    if (form.middle_name && !validateName(form.middle_name)) {
      setError('Middle name must contain only letters, spaces, apostrophes, or hyphens.');
      setLoading(false);
      return;
    }

    if (!validateEmailAddress(form.email)) {
      setError('Please enter a valid email address.');
      setLoading(false);
      return;
    }

    if (!validateNigerianPhone(form.phone)) {
      setError('Phone number must be a valid Nigerian mobile number.');
      setLoading(false);
      return;
    }

    if (!validateIdentity(form.nin) || !validateIdentity(form.bvn) || !/^\d{4}$/.test(form.pin)) {
      setError('NIN and BVN must each be exactly 11 digits, and PIN must be exactly 4 digits.');
      setLoading(false);
      return;
    }

    if (form.pin !== form.pin_confirmation) {
      setError('The transfer PINs do not match.');
      setLoading(false);
      return;
    }

    if (!validatePassword(form.password)) {
      setError('Password must be at least 8 characters long, include at least one number, and include at least one special character.');
      setLoading(false);
      return;
    }

    if (form.password !== form.password_confirmation) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }

    if (!emailVerified) {
      setError('Please verify your email before creating the account.');
      setLoading(false);
      return;
    }

    try {
      const registrationData = {
        ...form,
        name: fullName,
      };
      delete registrationData.pin_confirmation;
      delete registrationData.password_confirmation;
      const response = await api.post('/auth/register', registrationData);
      if (response?.data) {
        navigate('/login');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-4 py-6 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col overflow-hidden rounded-[32px] border border-white/70 bg-white/80 shadow-2xl backdrop-blur lg:flex-row">
        <div className="flex flex-1 flex-col justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-8 text-white sm:p-10 lg:p-14">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Open an account</p>
          <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Create a new SirKome Bank customer profile</h1>
          <p className="mt-4 max-w-md text-base text-slate-300">
            Register a new user and use the admin account to transfer funds into their account for a complete demo.
          </p>
        </div>

        <div className="flex flex-1 items-center justify-center p-6 sm:p-8 lg:p-10">
          <form onSubmit={handleSubmit} className="w-full max-w-xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-lg sm:p-8">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-600">Sign up</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">Create your bank account</h2>

            {emailVerified ? (
              <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
                Email verified successfully. Create your account below.
              </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="first_name">
                  First name
                </label>
                <input id="first_name" name="first_name" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.first_name} onChange={handleChange} required />
                <ValidationMessage message={getValidationMessage('first_name', form.first_name, form)} />
              </div>
              <div>
                <label className="mt-6 block text-sm font-medium text-slate-700" htmlFor="last_name">
                  Last name
                </label>
                <input id="last_name" name="last_name" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.last_name} onChange={handleChange} required />
                <ValidationMessage message={getValidationMessage('last_name', form.last_name, form)} />
              </div>
            </div>

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="middle_name">
              Middle name (optional)
            </label>
            <input id="middle_name" name="middle_name" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.middle_name} onChange={handleChange} />
            <ValidationMessage message={getValidationMessage('middle_name', form.middle_name, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="email">
              Email <span className="text-rose-500">*</span>
            </label>
            <input id="email" name="email" type="email" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.email} onChange={handleChange} required />
            <ValidationMessage message={getValidationMessage('email', form.email, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="phone">
              Phone number <span className="text-rose-500">*</span>
            </label>
            <input id="phone" name="phone" className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.phone} onChange={handleChange} required />
            <ValidationMessage message={getValidationMessage('phone', form.phone, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="nin">
              NIN <span className="text-rose-500">*</span>
            </label>
            <input id="nin" name="nin" inputMode="numeric" maxLength={11} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.nin} onChange={handleChange} required />
            <ValidationMessage message={getValidationMessage('nin', form.nin, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="bvn">
              BVN <span className="text-rose-500">*</span>
            </label>
            <input id="bvn" name="bvn" inputMode="numeric" maxLength={11} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" value={form.bvn} onChange={handleChange} required />
            <ValidationMessage message={getValidationMessage('bvn', form.bvn, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="password">
              Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-2">
              <input id="password" name="password" type={showPassword ? 'text' : 'password'} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" value={form.password} onChange={handleChange} required />
              <button
                type="button"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((current) => !current)}
                className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-700"
              >
                {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            <ValidationMessage message={getValidationMessage('password', form.password, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="password_confirmation">
              Confirm password <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-2">
              <input id="password_confirmation" name="password_confirmation" type={showPasswordConfirmation ? 'text' : 'password'} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" value={form.password_confirmation} onChange={handleChange} required />
              <button
                type="button"
                aria-label={showPasswordConfirmation ? 'Hide confirmed password' : 'Show confirmed password'}
                onClick={() => setShowPasswordConfirmation((current) => !current)}
                className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-700"
              >
                {showPasswordConfirmation ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            <ValidationMessage message={getValidationMessage('password_confirmation', form.password_confirmation, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="pin">
              4-digit transfer PIN <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-2">
              <input id="pin" name="pin" type={showPin ? 'text' : 'password'} inputMode="numeric" maxLength={4} pattern="\d{4}" className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" value={form.pin} onChange={handleChange} required />
              <button
                type="button"
                aria-label={showPin ? 'Hide transfer PIN' : 'Show transfer PIN'}
                onClick={() => setShowPin((current) => !current)}
                className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-700"
              >
                {showPin ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            <ValidationMessage message={getValidationMessage('pin', form.pin, form)} />

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="pin_confirmation">
              Confirm 4-digit transfer PIN <span className="text-rose-500">*</span>
            </label>
            <div className="relative mt-2">
              <input id="pin_confirmation" name="pin_confirmation" type={showPinConfirmation ? 'text' : 'password'} inputMode="numeric" maxLength={4} pattern="\d{4}" className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" value={form.pin_confirmation} onChange={handleChange} required />
              <button
                type="button"
                aria-label={showPinConfirmation ? 'Hide confirmed transfer PIN' : 'Show confirmed transfer PIN'}
                onClick={() => setShowPinConfirmation((current) => !current)}
                className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-700"
              >
                {showPinConfirmation ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            <ValidationMessage message={getValidationMessage('pin_confirmation', form.pin_confirmation, form)} />

            {error ? (
              <div className="mt-4 text-sm text-rose-600">
                <p>{error}</p>
                {error.toLowerCase().includes('existing user') ? (
                  <a href="/login" className="mt-1 inline-block font-medium text-cyan-700 underline">Go to login</a>
                ) : null}
              </div>
            ) : null}

            {!emailVerified ? (
              <button type="button" disabled={verificationLoading} onClick={sendVerificationCode} className="mt-6 w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70">
                {verificationLoading ? 'Sending code...' : 'Send verification code'}
              </button>
            ) : null}
            {emailVerified ? (
              <button type="submit" disabled={loading} className="mt-6 w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70">
                {loading ? 'Creating account...' : 'Create account'}
              </button>
            ) : null}

            <p className="mt-4 text-center text-sm text-slate-500">
              Already registered? <a href="/login" className="font-medium text-cyan-600">Sign in</a>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Register;
