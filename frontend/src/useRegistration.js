import { useContext } from 'react';

import registrationContextValue from './registrationContextValue';

export default function useRegistration() {
  return useContext(registrationContextValue);
}
