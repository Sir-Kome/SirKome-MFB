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

export default MobileBottomNav;
