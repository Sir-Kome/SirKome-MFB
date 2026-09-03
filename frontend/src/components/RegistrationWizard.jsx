import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { useMemo, useState } from 'react';

const steps = [
  { id: 'name', label: 'Name' },
  { id: 'email', label: 'Email' },
  { id: 'phone', label: 'Phone' },
  { id: 'personal', label: 'Personal Info' },
  { id: 'identity', label: 'Identity' },
  { id: 'security', label: 'Security' },
  { id: 'verification', label: 'Verification' },
];

const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim());
const isValidPhone = (value) => /^(\+234|234|0)\d{10}$/.test((value || '').replace(/\s+/g, ''));
const isValidName = (value) => /^[A-Za-z][A-Za-z\s'-]*$/.test((value || '').trim());
const isValidPin = (value) => /^\d{4}$/.test(value || '');
const isValidPassword = (value) => /^(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,}$/.test(value || '');
const isValidIdentity = (value) => /^\d{11}$/.test(value || '');

function RegistrationWizard({ initialDraft, onSubmit, onCancel, onVerifiedEmail, sendingCode, setSendingCode }) {
  const [form, setForm] = useState(initialDraft || {
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
  });
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [showPin, setShowPin] = useState(false);
  const [showPinConfirmation, setShowPinConfirmation] = useState(false);

  const stepNames = useMemo(() => steps.map((item) => item.id), []);

  const persistDraft = (nextForm) => {
    sessionStorage.setItem('sirkome_registration_draft', JSON.stringify(nextForm));
  };

  const updateField = (name, value) => {
    const sanitized = name === 'phone'
      ? value.replace(/[^\d+\s]/g, '').slice(0, 20)
      : name === 'first_name' || name === 'last_name' || name === 'middle_name'
        ? value.replace(/[^A-Za-z\s'-]/g, '')
        : name === 'nin' || name === 'bvn'
          ? value.replace(/\D/g, '').slice(0, 11)
          : name === 'pin' || name === 'pin_confirmation'
            ? value.replace(/\D/g, '').slice(0, 4)
            : value;

    const nextForm = { ...form, [name]: sanitized };
    setForm(nextForm);
    persistDraft(nextForm);
    setErrors((current) => ({ ...current, [name]: '' }));
  };

  const validateCurrentStep = () => {
    const nextErrors = {};

    if (stepNames[step] === 'name') {
      if (!form.first_name.trim()) nextErrors.first_name = 'First name is required.';
      else if (!isValidName(form.first_name)) nextErrors.first_name = 'Use letters, spaces, apostrophes, or hyphens only.';
      if (!form.last_name.trim()) nextErrors.last_name = 'Last name is required.';
      else if (!isValidName(form.last_name)) nextErrors.last_name = 'Use letters, spaces, apostrophes, or hyphens only.';
      if (form.middle_name && !isValidName(form.middle_name)) nextErrors.middle_name = 'Middle name is invalid.';
    }

    if (stepNames[step] === 'email') {
      if (!form.email.trim()) nextErrors.email = 'Email is required.';
      else if (!isValidEmail(form.email)) nextErrors.email = 'Enter a valid email address.';
    }

    if (stepNames[step] === 'phone') {
      if (!form.phone.trim()) nextErrors.phone = 'Phone number is required.';
      else if (!isValidPhone(form.phone)) nextErrors.phone = 'Enter a valid Nigerian mobile number.';
    }

    if (stepNames[step] === 'personal') {
      if (!form.date_of_birth) nextErrors.date_of_birth = 'Date of birth is required.';
      if (!form.gender) nextErrors.gender = 'Please select your gender.';
    }

    if (stepNames[step] === 'identity') {
      const selectedIdentity = form.identity_type || 'nin';
      const value = form[selectedIdentity];
      if (!value) nextErrors[selectedIdentity] = `Please enter your ${selectedIdentity.toUpperCase()}.`;
      else if (!isValidIdentity(value)) nextErrors[selectedIdentity] = 'Identity number must be 11 digits.';
    }

    if (stepNames[step] === 'security') {
      if (!form.password) nextErrors.password = 'Password is required.';
      else if (!isValidPassword(form.password)) nextErrors.password = 'Use 8+ characters, one number, and one special character.';
      if (!form.password_confirmation) nextErrors.password_confirmation = 'Confirm your password.';
      else if (form.password !== form.password_confirmation) nextErrors.password_confirmation = 'Passwords do not match.';
      if (!form.pin) nextErrors.pin = 'Transfer PIN is required.';
      else if (!isValidPin(form.pin)) nextErrors.pin = 'PIN must be exactly 4 digits.';
      if (!form.pin_confirmation) nextErrors.pin_confirmation = 'Confirm your transfer PIN.';
      else if (form.pin !== form.pin_confirmation) nextErrors.pin_confirmation = 'PINs do not match.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const currentStepId = stepNames[step];

  const goNext = () => {
    if (!validateCurrentStep()) return;
    if (step < steps.length - 1) {
      setStep((current) => current + 1);
    }
  };

  const goBack = () => {
    setStep((current) => Math.max(0, current - 1));
  };

  const handleSubmit = async () => {
    if (!validateCurrentStep()) return;
    await onSubmit({
      ...form,
      name: `${form.first_name} ${form.last_name}`.trim(),
    });
  };

  const renderStep = () => {
    if (currentStepId === 'name') {
      return (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700">First name</label>
              <input value={form.first_name} onChange={(event) => updateField('first_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
              {errors.first_name ? <p className="mt-1 text-xs text-rose-600">{errors.first_name}</p> : null}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Last name</label>
              <input value={form.last_name} onChange={(event) => updateField('last_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
              {errors.last_name ? <p className="mt-1 text-xs text-rose-600">{errors.last_name}</p> : null}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Middle name (optional)</label>
            <input value={form.middle_name} onChange={(event) => updateField('middle_name', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            {errors.middle_name ? <p className="mt-1 text-xs text-rose-600">{errors.middle_name}</p> : null}
          </div>
        </div>
      );
    }

    if (currentStepId === 'email') {
      return (
        <div>
          <label className="block text-sm font-medium text-slate-700">Email address</label>
          <input type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
          {errors.email ? <p className="mt-1 text-xs text-rose-600">{errors.email}</p> : null}
        </div>
      );
    }

    if (currentStepId === 'phone') {
      return (
        <div>
          <label className="block text-sm font-medium text-slate-700">Phone number</label>
          <input value={form.phone} onChange={(event) => updateField('phone', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
          {errors.phone ? <p className="mt-1 text-xs text-rose-600">{errors.phone}</p> : null}
        </div>
      );
    }

    if (currentStepId === 'personal') {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Date of birth</label>
            <input type="date" value={form.date_of_birth} onChange={(event) => updateField('date_of_birth', event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" />
            {errors.date_of_birth ? <p className="mt-1 text-xs text-rose-600">{errors.date_of_birth}</p> : null}
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
            {errors.gender ? <p className="mt-1 text-xs text-rose-600">{errors.gender}</p> : null}
          </div>
        </div>
      );
    }

    if (currentStepId === 'identity') {
      return (
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
            <input value={form[form.identity_type]} onChange={(event) => updateField(form.identity_type, event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" maxLength={11} />
            {errors[form.identity_type] ? <p className="mt-1 text-xs text-rose-600">{errors[form.identity_type]}</p> : null}
          </div>
        </div>
      );
    }

    if (currentStepId === 'security') {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Password</label>
            <div className="relative mt-2">
              <input type={showPassword ? 'text' : 'password'} value={form.password} onChange={(event) => updateField('password', event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" />
              <button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute inset-y-0 right-3 flex items-center text-slate-500">
                {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            {errors.password ? <p className="mt-1 text-xs text-rose-600">{errors.password}</p> : null}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Confirm password</label>
            <div className="relative mt-2">
              <input type={showPasswordConfirmation ? 'text' : 'password'} value={form.password_confirmation} onChange={(event) => updateField('password_confirmation', event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" />
              <button type="button" onClick={() => setShowPasswordConfirmation((current) => !current)} className="absolute inset-y-0 right-3 flex items-center text-slate-500">
                {showPasswordConfirmation ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            {errors.password_confirmation ? <p className="mt-1 text-xs text-rose-600">{errors.password_confirmation}</p> : null}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Transfer PIN</label>
            <div className="relative mt-2">
              <input type={showPin ? 'text' : 'password'} value={form.pin} onChange={(event) => updateField('pin', event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" maxLength={4} inputMode="numeric" />
              <button type="button" onClick={() => setShowPin((current) => !current)} className="absolute inset-y-0 right-3 flex items-center text-slate-500">
                {showPin ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            {errors.pin ? <p className="mt-1 text-xs text-rose-600">{errors.pin}</p> : null}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Confirm transfer PIN</label>
            <div className="relative mt-2">
              <input type={showPinConfirmation ? 'text' : 'password'} value={form.pin_confirmation} onChange={(event) => updateField('pin_confirmation', event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12" maxLength={4} inputMode="numeric" />
              <button type="button" onClick={() => setShowPinConfirmation((current) => !current)} className="absolute inset-y-0 right-3 flex items-center text-slate-500">
                {showPinConfirmation ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </button>
            </div>
            {errors.pin_confirmation ? <p className="mt-1 text-xs text-rose-600">{errors.pin_confirmation}</p> : null}
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">Email verification is the final step. You will be sent a code before your account is created.</div>
        <button
          type="button"
          onClick={async () => {
            if (!form.email || !isValidEmail(form.email)) {
              setErrors({ email: 'Enter a valid email address before requesting a code.' });
              return;
            }
            setSendingCode(true);
            await onVerifiedEmail(form.email);
          }}
          className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white"
        >
          {sendingCode ? 'Sending code...' : 'Send verification code'}
        </button>
      </div>
    );
  };

  return (
    <div className="w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-lg sm:p-8">
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {steps.map((item, index) => {
          const active = index === step;
          const complete = index < step;
          return (
            <div key={item.id} className="flex items-center">
              <button type="button" disabled={index > step} onClick={() => index <= step && setStep(index)} className={`rounded-full px-3 py-1 text-xs font-semibold ${active ? 'bg-cyan-600 text-white' : complete ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                {item.label}
              </button>
              {index < steps.length - 1 ? <span className="mx-1 text-slate-300">→</span> : null}
            </div>
          );
        })}
      </div>

      <div className="mb-6">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-600">Registration</p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">{steps[step].label}</h2>
      </div>

      {renderStep()}

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button type="button" onClick={onCancel} className="rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700">Cancel</button>
        <div className="flex gap-3">
          {step > 0 ? <button type="button" onClick={goBack} className="rounded-2xl border border-slate-300 px-4 py-3 font-semibold text-slate-700">Back</button> : null}
          {step < steps.length - 1 ? (
            <button type="button" onClick={goNext} className="rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white">Next</button>
          ) : (
            <button type="button" onClick={handleSubmit} className="rounded-2xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white">Create account</button>
          )}
        </div>
      </div>
    </div>
  );
}

export default RegistrationWizard;
