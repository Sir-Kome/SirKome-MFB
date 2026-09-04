import { AccountBalance, History, Home, Person, Send } from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

function MobileBottomNav({ items }) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <nav className="mobile-bottom-nav" aria-label="Primary navigation">
      {items.map((item) => {
        const active = location.pathname === item.path || (item.path === '/dashboard' && location.pathname === '/');
        return (
          <button key={item.path} type="button" onClick={() => navigate(item.path)} className={active ? 'mobile-bottom-nav__item mobile-bottom-nav__item--active' : 'mobile-bottom-nav__item'}>
            {item.icon}
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

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

export default MobileBottomNav;
