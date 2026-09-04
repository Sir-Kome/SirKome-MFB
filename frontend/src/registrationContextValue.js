import { createContext } from 'react';

const registrationContextValue = createContext({
  secrets: {},
  setSecrets: () => {},
});

export default registrationContextValue;
