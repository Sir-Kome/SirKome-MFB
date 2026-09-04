import { useState } from 'react';

import registrationContextValue from './registrationContextValue';

const RegistrationContextValue = registrationContextValue;

export function RegistrationProvider({ children }) {
  const [secrets, setSecrets] = useState({});
  return <RegistrationContextValue.Provider value={{ secrets, setSecrets }}>{children}</RegistrationContextValue.Provider>;
}
