function Navbar({ user }) {
  return (
    <header className="flex flex-col gap-3 rounded-[28px] border border-slate-200/70 bg-white/80 p-5 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">Good morning</p>
        <h1 className="text-2xl font-semibold text-slate-900">Welcome back, {user?.name || 'Sarah'}</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-slate-100 p-3 text-slate-600">🔔</div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 font-semibold text-white">
          S
        </div>
      </div>
    </header>
  );
}

export default Navbar;