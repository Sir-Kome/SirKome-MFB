import { AccountBalance, History, Home, Person, Send } from '@mui/icons-material';

export const customerMobileItems = [
  { label: 'Home', icon: <Home fontSize="small" />, path: '/dashboard' },
  { label: 'Accounts', icon: <AccountBalance fontSize="small" />, path: '/accounts' },
  { label: 'Transfer', icon: <Send fontSize="small" />, path: '/transfer' },
  { label: 'History', icon: <History fontSize="small" />, path: '/transactions' },
  { label: 'Profile', icon: <Person fontSize="small" />, path: '/profile' },
];

export const adminMobileItems = [
  { label: 'Home', icon: <Home fontSize="small" />, path: '/admin-dashboard' },
  { label: 'Transfer', icon: <Send fontSize="small" />, path: '/transfer' },
  { label: 'Users', icon: <Person fontSize="small" />, path: '/admin/users' },
];
