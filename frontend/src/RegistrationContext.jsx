import { createContext, useContext, useState } from 'react';

const RegistrationContext = createContext({
  secrets: {},
  setSecrets: () => {},
});

export function RegistrationProvider({ children }) {
  const [secrets, setSecrets] = useState({});
  return <RegistrationContext.Provider value={{ secrets, setSecrets }}>{children}</RegistrationContext.Provider>;
}

export function useRegistration() {
  return useContext(RegistrationContext);
}
