import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import useRegistration from '../useRegistration';
import api from '../services/api';
import { registerUser } from '../services/registration';

const steps = [
  { id: 'name', label: 'Name' },
  { id: 'email', label: 'Email' },
  { id: 'phone', label: 'Phone' },
  { id: 'personal', label: 'Personal Info' },
  { id: 'identity', label: 'Identity' },
  { id: 'security', label: 'Security' },
  { id: 'verification', label: 'Verification' },
];

const emptyForm = {
  first_name: '',
  last_name: '',
  middle_name: '',
  email: '',
  phone: '',
  date_of_birth: '',
  gender: '',
  identity_type: 'nin',
  nin: '',
  bvn: '',
  password: '',
  password_confirmation: '',
  pin: '',
  pin_confirmation: '',
};

const validateEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim());
const validateName = (value) => /^[A-Za-z][A-Za-z\s'-]*$/.test((value || '').trim());
const validatePhone = (value) => /^(\+234|234|0)\d{10}$/.test((value || '').replace(/\s+/g, ''));
const validatePassword = (value) => /^(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,}$/.test(value || '');
const validateIdentity = (value) => /^\d{11}$/.test(value || '');
const validatePin = (value) => /^\d{4}$/.test(value || '');

const getFieldError = (name, value, form) => {
  if (name === 'first_name' || name === 'last_name') {
    if (!value.trim()) return `${name === 'first_name' ? 'First' : 'Last'} name is required.`;
    return validateName(value) ? '' : 'Use letters, spaces, apostrophes, or hyphens only.';
  }
  if (name === 'middle_name') return value && !validateName(value) ? 'Middle name is invalid.' : '';
  if (name === 'email') {
    if (!value.trim()) return 'Email is required.';
    return validateEmail(value) ? '' : 'Please enter a valid email address.';
  }
  if (name === 'phone') {
    if (!value.trim()) return 'Phone number is required.';
    return validatePhone(value) ? '' : 'Enter a valid Nigerian mobile number.';
  }
  if (name === 'date_of_birth') {
    if (!value) return 'Date of birth is required.';
    return value > new Date().toISOString().split('T')[0] ? 'Date of birth cannot be in the future.' : '';
  }
  if (name === 'gender') return value ? '' : 'Please select your gender.';
  if (name === 'nin' || name === 'bvn') return validateIdentity(value) ? '' : `${name.toUpperCase()} must contain exactly 11 digits.`;
  if (name === 'password') return validatePassword(value) ? '' : 'Use 8+ characters, one number, and one special character.';
  if (name === 'password_confirmation') return value === form.password ? '' : 'Passwords do not match.';
  if (name === 'pin') return validatePin(value) ? '' : 'PIN must contain exactly 4 digits.';
  if (name === 'pin_confirmation') return value === form.pin ? '' : 'PINs do not match.';
  return '';
};

function Register() {
  const navigate = useNavigate();
  const location = useLocation();
  const { secrets, setSecrets } = useRegistration();
  const returningFromVerification = Boolean(location.state?.emailVerified);
  const [form, setForm] = useState(() => {
    if (!returningFromVerification) {
      sessionStorage.removeItem('sirkome_registration_draft');
      return emptyForm;
    }

    let saved = null;
    try {
      saved = JSON.parse(sessionStorage.getItem('sirkome_registration_draft') || 'null');
    } catch {
      sessionStorage.removeItem('sirkome_registration_draft');
    }
    return saved ? { ...emptyForm, ...saved, ...secrets } : { ...emptyForm, ...secrets };
  });
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [emailVerified] = useState(returningFromVerification);
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    if (!returningFromVerification) {
      setSecrets({});
    }
  }, [returningFromVerification, setSecrets]);

  const persistDraft = (nextForm) => {
    const draft = { ...nextForm };
    delete draft.password;
    delete draft.password_confirmation;
    delete draft.pin;
    delete draft.pin_confirmation;
    sessionStorage.setItem('sirkome_registration_draft', JSON.stringify(draft));
  };

  const updateField = (key, value) => {
    const sanitized = key === 'phone'
      ? value.replace(/[^\d+\s]/g, '').slice(0, 20)
      : key === 'first_name' || key === 'last_name' || key === 'middle_name'
        ? value.replace(/[^A-Za-z\s'-]/g, '')
        : key === 'nin' || key === 'bvn'
          ? value.replace(/\D/g, '').slice(0, 11)
          : key === 'pin' || key === 'pin_confirmation'
            ? value.replace(/\D/g, '').slice(0, 4)
            : value;

    const next = { ...form, [key]: sanitized };
    setForm(next);
    if (['password', 'password_confirmation', 'pin', 'pin_confirmation'].includes(key)) {
      setSecrets((current) => ({ ...current, [key]: sanitized }));
    }
    persistDraft(next);
    const nextErrors = { ...fieldErrors };
    if (['nin', 'bvn'].includes(key) && key !== next.identity_type) {
      delete nextErrors[key];
    } else {
      const fieldError = getFieldError(key, sanitized, next);
      if (fieldError) nextErrors[key] = fieldError;
      else delete nextErrors[key];
    }
    if (key === 'password') {
      const confirmationError = getFieldError('password_confirmation', next.password_confirmation, next);
      if (confirmationError) nextErrors.password_confirmation = confirmationError;
      else delete nextErrors.password_confirmation;
    }
    if (key === 'pin') {
      const confirmationError = getFieldError('pin_confirmation', next.pin_confirmation, next);
      if (confirmationError) nextErrors.pin_confirmation = confirmationError;
      else delete nextErrors.pin_confirmation;
    }
    setFieldErrors(nextErrors);
    setError('');
  };

  const validateCurrentStep = () => {
    const nextErrors = {};
    const currentStep = steps[stepIndex]?.id;

    if (currentStep === 'name') {
      if (!form.first_name.trim()) nextErrors.first_name = 'First name is required.';
      else if (!validateName(form.first_name)) nextErrors.first_name = 'Use letters, spaces, apostrophes, or hyphens only.';
      if (!form.last_name.trim()) nextErrors.last_name = 'Last name is required.';
      else if (!validateName(form.last_name)) nextErrors.last_name = 'Use letters, spaces, apostrophes, or hyphens only.';
      if (form.middle_name && !validateName(form.middle_name)) nextErrors.middle_name = 'Middle name is invalid.';
    }

    if (currentStep === 'email') {
      if (!form.email.trim()) nextErrors.email = 'Email is required.';
      else if (!validateEmail(form.email)) nextErrors.email = 'Please enter a valid email address.';
    }

    if (currentStep === 'phone') {
      if (!form.phone.trim()) nextErrors.phone = 'Phone number is required.';
      else if (!validatePhone(form.phone)) nextErrors.phone = 'Enter a valid Nigerian mobile number.';
    }

    if (currentStep === 'personal') {
      if (!form.date_of_birth) nextErrors.date_of_birth = 'Date of birth is required.';
      if (!form.gender) nextErrors.gender = 'Please select your gender.';
    }

    if (currentStep === 'identity') {
      const identityKey = form.identity_type || 'nin';
      if (!validateIdentity(form[identityKey])) nextErrors[identityKey] = 'Identity number must contain 11 digits.';
    }

    if (currentStep === 'security') {
      if (!validatePassword(form.password)) nextErrors.password = 'Use 8+ characters, one number, and one special character.';
      if (!form.password_confirmation) nextErrors.password_confirmation = 'Please confirm your password.';
      else if (form.password !== form.password_confirmation) nextErrors.password_confirmation = 'Passwords do not match.';
      if (!validatePin(form.pin)) nextErrors.pin = 'PIN must contain exactly 4 digits.';
      if (!form.pin_confirmation) nextErrors.pin_confirmation = 'Please confirm your PIN.';
      else if (form.pin !== form.pin_confirmation) nextErrors.pin_confirmation = 'PINs do not match.';
    }

    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    setStepIndex((current) => Math.min(current + 1, steps.length - 1));
  };

  const goBack = () => setStepIndex((current) => Math.max(current - 1, 0));

  const sendVerificationCode = async () => {
    if (!validateEmail(form.email)) {
      setFieldErrors((current) => ({ ...current, email: 'Please enter a valid email address.' }));
      setError('Please enter a valid email before sending a verification code.');
      return;
    }
    setSendingCode(true);
    setError('');
    try {
      await api.post('/auth/send-verification', { email: form.email });
      persistDraft(form);
      navigate('/verify-email', { state: { email: form.email } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to send verification code.');
    } finally {
      setSendingCode(false);
    }
  };

  const handleSubmit = async () => {
    if (!validateCurrentStep()) return;
    if (!emailVerified) {
      setError('Verify your email before creating the account.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await registerUser(form);
      if (response?.data) {
        sessionStorage.removeItem('sirkome_registration_draft');
        navigate('/login');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create account.');
    } finally {
      setLoading(false);
    }
  };

  const currentStep = steps[stepIndex];
  const summary = useMemo(() => [
    { label: 'Name', value: `${form.first_name || ''} ${form.last_name || ''}`.trim() || 'Not set' },
    { label: 'Email', value: form.email || 'Not set' },
    { label: 'Phone', value: form.phone || 'Not set' },
  ], [form]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),linear-gradient(135deg,_#f4f7ff_0%,_#eef2ff_100%)] px-3 py-4 text-slate-800 sm:px-6 sm:py-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-5xl flex-col overflow-hidden rounded-[28px] border border-white/70 bg-white/80 shadow-2xl backdrop-blur sm:min-h-[calc(100vh-3rem)] sm:rounded-[32px] lg:flex-row">
        <div className="hidden flex-1 flex-col justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-8 text-white lg:flex lg:p-14">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">Open an account</p>
          <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Register in a few guided steps</h1>
          <p className="mt-4 max-w-md text-base text-slate-300">The process is split into simple steps and the verification code is the final step before your account is created.</p>
          <div className="mt-8 space-y-3">
            {summary.map((item) => (
              <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
                <span className="block text-xs uppercase tracking-[0.2em] text-cyan-300">{item.label}</span>
                <span className="mt-1 block font-medium text-white">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-2 py-6 sm:p-8 lg:p-10">
          <div className="w-full max-w-2xl rounded-[24px] border border-slate-200 bg-white p-5 shadow-lg sm:rounded-[28px] sm:p-8">
            <div className="mb-6 flex items-center gap-3 lg:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 font-semibold text-white">SB</div>
              <div><p className="text-xs uppercase tracking-[0.2em] text-slate-500">SirKome Bank</p><p className="font-semibold text-slate-900">Create your account</p></div>
            </div>
            <div className="mb-5 lg:hidden">
              <div className="flex items-center justify-between text-sm font-semibold text-slate-700"><span>Step {stepIndex + 1} of {steps.length}</span><span>{currentStep.label}</span></div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 transition-all" style={{ width: `${((stepIndex + 1) / steps.length) * 100}%` }} /></div>
            </div>
            <div className="mb-6 flex flex-wrap items-center gap-2">
              {steps.map((item, index) => {
                const active = index === stepIndex;
                const done = index < stepIndex;
                return (
                  <div key={item.id} className="flex items-center">
                    <button type="button" onClick={() => index <= stepIndex && setStepIndex(index)} className={`rounded-full px-3 py-1 text-xs font-semibold ${active ? 'bg-cyan-600 text-white' : done ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {item.label}
                    </button>
                    {index < steps.length - 1 && <span className="mx-1 text-slate-300">→</span>}
                  </div>
                );
              })}
            </div>

            {currentStep.id === 'name' && (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-slate-700">First name</label>
                    <input value={form.first_name} onChange={(event) => updateField('first_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                    {fieldErrors.first_name ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.first_name}</p> : null}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Last name</label>
                    <input value={form.last_name} onChange={(event) => updateField('last_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                    {fieldErrors.last_name ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.last_name}</p> : null}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Middle name (optional)</label>
                  <input value={form.middle_name} onChange={(event) => updateField('middle_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                  {fieldErrors.middle_name ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.middle_name}</p> : null}
                </div>
              </div>
            )}

            {currentStep.id === 'email' && (
              <div>
                <label className="block text-sm font-medium text-slate-700">Email address</label>
                <input type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                {fieldErrors.email ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.email}</p> : null}
              </div>
            )}

            {currentStep.id === 'phone' && (
              <div>
                <label className="block text-sm font-medium text-slate-700">Phone number</label>
                <input type="tel" autoComplete="tel" value={form.phone} onChange={(event) => updateField('phone', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                {fieldErrors.phone ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.phone}</p> : null}
              </div>
            )}

            {currentStep.id === 'personal' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Date of birth</label>
                  <input type="date" value={form.date_of_birth} onChange={(event) => updateField('date_of_birth', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                  {fieldErrors.date_of_birth ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.date_of_birth}</p> : null}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Gender</label>
                  <select value={form.gender} onChange={(event) => updateField('gender', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <option value="">Select</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </select>
                  {fieldErrors.gender ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.gender}</p> : null}
                </div>
              </div>
            )}

            {currentStep.id === 'identity' && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-slate-700">Verification type</p>
                  <div className="mt-2 flex gap-3">
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                      <input type="radio" checked={form.identity_type === 'nin'} onChange={() => updateField('identity_type', 'nin')} />
                      NIN
                    </label>
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                      <input type="radio" checked={form.identity_type === 'bvn'} onChange={() => updateField('identity_type', 'bvn')} />
                      BVN
                    </label>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">{form.identity_type === 'nin' ? 'NIN' : 'BVN'} number</label>
                  <input inputMode="numeric" autoComplete="off" value={form[form.identity_type]} onChange={(event) => updateField(form.identity_type, event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" maxLength={11} />
                  {fieldErrors[form.identity_type] ? <p className="mt-1 text-xs text-rose-600">{fieldErrors[form.identity_type]}</p> : null}
                </div>
              </div>
            )}

            {currentStep.id === 'security' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Password</label>
                  <input type="password" autoComplete="new-password" value={form.password} onChange={(event) => updateField('password', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                  {fieldErrors.password ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.password}</p> : null}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Confirm password</label>
                  <input type="password" value={form.password_confirmation} onChange={(event) => updateField('password_confirmation', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
                  {fieldErrors.password_confirmation ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.password_confirmation}</p> : null}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Transfer PIN</label>
                  <input type="password" value={form.pin} onChange={(event) => updateField('pin', event.target.value)} maxLength={4} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" inputMode="numeric" />
                  {fieldErrors.pin ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.pin}</p> : null}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Confirm transfer PIN</label>
                  <input type="password" value={form.pin_confirmation} onChange={(event) => updateField('pin_confirmation', event.target.value)} maxLength={4} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" inputMode="numeric" />
                  {fieldErrors.pin_confirmation ? <p className="mt-1 text-xs text-rose-600">{fieldErrors.pin_confirmation}</p> : null}
                </div>
              </div>
            )}

            {currentStep.id === 'verification' && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
                  The verification code is the final step. Verify your email now, then create the account.
                </div>
                <button type="button" onClick={sendVerificationCode} disabled={sendingCode} className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white disabled:opacity-70">
                  {sendingCode ? 'Sending code...' : 'Send verification code'}
                </button>
                {emailVerified && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">Email verified successfully. Finish creating your account below.</div>}
                <button type="button" onClick={handleSubmit} disabled={loading || !emailVerified} className="w-full rounded-2xl bg-slate-900 px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
                  {loading ? 'Creating account...' : 'Create account'}
                </button>
              </div>
            )}

            {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
              <button type="button" onClick={() => navigate('/login')} className="rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700">Cancel</button>
              <div className="flex gap-3">
                {stepIndex > 0 && <button type="button" onClick={goBack} className="rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700">Back</button>}
                {stepIndex < steps.length - 1 ? (
                  <button type="button" onClick={goNext} className="rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white">Next</button>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;
