import { useEffect, useMemo, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import Accounts from './pages/Accounts';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
import Register from './pages/Register';
import Transfer from './pages/Transfer';
import Transactions from './pages/Transactions';
import VerifyEmail from './pages/VerifyEmail';
import { RegistrationProvider } from './RegistrationContext';
import { ThemeContext } from './ThemeContext';

function App() {
  const [theme, setTheme] = useState(() => {
    const storedTheme = localStorage.getItem('sirkome_theme');
    return storedTheme || 'light';
  });

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem('sirkome_theme', theme);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      toggleTheme: () => setTheme((current) => (current === 'light' ? 'dark' : 'light')),
    }),
    [theme],
  );

  return (
    <ThemeContext.Provider value={value}>
      <RegistrationProvider>
        <BrowserRouter>
          <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admin-dashboard" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/transfer" element={<Transfer />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </RegistrationProvider>
    </ThemeContext.Provider>
  );
}

export default App;