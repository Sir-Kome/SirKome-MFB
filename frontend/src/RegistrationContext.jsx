import { useState } from 'react';

import registrationContextValue from './registrationContextValue';

export function RegistrationProvider({ children }) {
  const [secrets, setSecrets] = useState({});
  return <registrationContextValue.Provider value={{ secrets, setSecrets }}>{children}</registrationContextValue.Provider>;
}
