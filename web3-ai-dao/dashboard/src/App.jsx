import { Routes, Route, NavLink } from 'react-router-dom';
import Overview from './pages/Overview';
import Proposals from './pages/Proposals';
import ProposalDetail from './pages/ProposalDetail';
import Bots from './pages/Bots';

function Sidebar() {
  const linkClass = ({ isActive }) =>
    `block px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-icarus-accent/20 text-icarus-accent-light' : 'text-icarus-muted hover:text-icarus-text hover:bg-icarus-card'
    }`;

  return (
    <aside className="w-56 border-r border-icarus-border h-screen flex flex-col">
      <div className="p-5 border-b border-icarus-border">
        <h1 className="font-bold text-lg">Icarus</h1>
        <p className="text-xs text-icarus-muted mt-0.5">DAO Dashboard</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        <NavLink to="/" end className={linkClass}>Overview</NavLink>
        <NavLink to="/proposals" className={linkClass}>Propostas</NavLink>
        <NavLink to="/bots" className={linkClass}>Bots</NavLink>
      </nav>
      <div className="p-3 border-t border-icarus-border">
        <p className="text-xs text-icarus-muted">Sepolia · Chain ID 11155111</p>
      </div>
    </aside>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 overflow-y-auto max-w-5xl">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/proposals" element={<Proposals />} />
          <Route path="/proposal/:id" element={<ProposalDetail />} />
          <Route path="/bots" element={<Bots />} />
        </Routes>
      </main>
    </div>
  );
}
