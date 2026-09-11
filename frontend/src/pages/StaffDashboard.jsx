import AdminDashboard from './AdminDashboard';
import TellerDashboard from './TellerDashboard';

function StaffDashboard() {
  const user = JSON.parse(sessionStorage.getItem('sirkome_user') || 'null');
  if (user?.role === 'TELLER') return <TellerDashboard />;
  return <AdminDashboard staffMode />;
}

export default StaffDashboard;
