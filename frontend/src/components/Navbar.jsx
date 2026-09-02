import { Close, DarkMode, LightMode, Notifications as NotificationsIcon } from '@mui/icons-material';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useTheme } from '../App';
import api from '../services/api';

function Navbar({ user }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(0);

  const loadNotifications = () => {
    const token = sessionStorage.getItem('sirkome_token');
    api.get('/notifications', { params: { page: 1, per_page: 5 }, headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        setNotifications(response.data?.items || []);
        setUnread(response.data?.unread || 0);
      })
      .catch(() => {});
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const deleteNotification = async (notificationId) => {
    const token = sessionStorage.getItem('sirkome_token');
    await api.delete(`/notifications/${notificationId}`, { headers: { Authorization: `Bearer ${token}` } });
    setNotifications((current) => current.filter((item) => item.id !== notificationId));
    setUnread((current) => Math.max(0, current - 1));
  };

  const clearNotifications = async () => {
    const token = sessionStorage.getItem('sirkome_token');
    await api.delete('/notifications', { headers: { Authorization: `Bearer ${token}` } });
    setNotifications([]);
    setUnread(0);
  };

  return (
    <header className="relative z-30 flex flex-col gap-3 rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">Good morning</p>
        <h1 className="text-2xl font-semibold text-slate-900">Welcome back, {user?.name || 'Sarah'}</h1>
      </div>
      <div className="flex items-center gap-3">
        <button type="button" onClick={toggleTheme} aria-label="Toggle theme" className="rounded-2xl border border-slate-200 bg-slate-100 p-3 text-slate-700 transition hover:bg-slate-200 dark-mode-button">
          {theme === 'light' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
        </button>
        <div className="relative">
          <button type="button" onClick={() => setOpen((current) => !current)} aria-label="Open notifications" className="relative rounded-2xl bg-slate-100 p-3 text-slate-600 transition hover:bg-slate-200 dark-mode-button">
            <NotificationsIcon fontSize="small" />
            {unread > 0 ? <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white">{unread > 9 ? '9+' : unread}</span> : null}
          </button>
          {open ? (
            <div className="absolute right-0 top-14 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-3 text-left shadow-2xl dark-mode-modal">
              <div className="flex items-center justify-between px-2 pb-2">
                <h2 className="font-semibold text-slate-900">Notifications</h2>
                <button type="button" onClick={clearNotifications} disabled={notifications.length === 0} className="text-xs font-medium text-rose-600 disabled:text-slate-300">Clear all</button>
              </div>
              <div className="max-h-72 space-y-2 overflow-auto">
                {notifications.length === 0 ? <p className="px-2 py-5 text-sm text-slate-500">No notifications yet.</p> : notifications.map((item) => (
                  <div key={item.id} className="rounded-xl bg-slate-50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800">{item.title}</p>
                      <button type="button" onClick={() => deleteNotification(item.id)} aria-label="Delete notification" title="Delete notification" className="text-slate-400 hover:text-rose-600"><Close fontSize="small" /></button>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-slate-600">{item.message}</p>
                    <p className="mt-2 text-[10px] text-slate-400">{item.created_at}</p>
                  </div>
                ))}
              </div>
              <button type="button" onClick={() => { setOpen(false); navigate('/notifications'); }} className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">View all notifications</button>
            </div>
          ) : null}
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 font-semibold text-white">
          S
        </div>
      </div>
    </header>
  );
}

export default Navbar;