import api from './api';

export function buildRegistrationPayload(form) {
  const payload = {
    ...form,
    name: `${form.first_name} ${form.last_name}`.trim(),
  };
  delete payload.password_confirmation;
  delete payload.pin_confirmation;
  return payload;
}

export function registerUser(form) {
  return api.post('/auth/register', buildRegistrationPayload(form));
}
