import { useState, useEffect } from 'react';
import { fetchStatus, fetchProposals, fetchRegistry, truncateAddress } from '../helpers/api';
import StatusCard from '../components/StatusCard';
import ProposalRow from '../components/ProposalRow';

export default function Overview() {
  const [status, setStatus] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [registry, setRegistry] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [s, p, r] = await Promise.all([fetchStatus(), fetchProposals(), fetchRegistry()]);
        if (!mounted) return;
        setStatus(s);
        setProposals(p.slice(-5).reverse());
        setRegistry(r);
      } catch (e) {
        if (mounted) setError(e.message);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 15000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-icarus-muted animate-pulse">Conectando ao indexer...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-icarus-card border border-icarus-red/30 rounded-xl p-6 text-center mt-8">
        <p className="text-icarus-red font-medium">Indexer não disponível</p>
        <p className="text-sm text-icarus-muted mt-1">{error}</p>
        <p className="text-xs text-icarus-muted mt-3">Execute <code className="bg-icarus-bg px-1 rounded">cd indexer && npm start</code></p>
      </div>
    );
  }

  if (!status) return null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold">Projeto Icarus</h1>
        <p className="text-icarus-muted text-sm mt-1">DAO Governance Dashboard</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatusCard title="Proposals" value={status.proposalCount} subtitle={`${status.executedCount} executadas`} color="text-icarus-accent-light" />
        <StatusCard title="Tesouro" value={`${status.treasuryBalance?.toLocaleString() || 0} AIGOV`} subtitle="DAO Treasury" color="text-icarus-green" />
        <StatusCard title="Total FOR" value={status.totalForVotes?.toLocaleString()} subtitle="Votos acumulados" color="text-icarus-green" />
        <StatusCard title="Total AGAINST" value={status.totalAgainstVotes?.toLocaleString()} subtitle="Votos acumulados" color="text-icarus-red" />
      </div>

      {(registry && registry.length > 0) && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-icarus-muted uppercase tracking-wider">Bots Registrados</h2>
            <a href="/bots" className="text-xs text-icarus-accent-light hover:underline">Ver todos →</a>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {registry.map(bot => {
              const statusBot = status.bots?.find(b => b.address.toLowerCase() === bot.address.toLowerCase());
              return (
                <div key={bot.id} className="bg-icarus-card border border-icarus-border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-sm font-bold">{bot.name}</p>
                      <p className="text-xs font-mono text-icarus-muted">{truncateAddress(bot.address)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">{statusBot?.tokens?.toFixed(0) || 0} AIGOV</p>
                      <p className="text-xs text-icarus-muted">{statusBot?.eth?.toFixed(4) || 0} ETH</p>
                    </div>
                  </div>
                  <p className="text-xs text-icarus-muted italic leading-relaxed mt-1">"{bot.manifesto}"</p>
                  {statusBot?.reputation && (
                    <p className="text-xs mt-2">
                      <span className="text-icarus-accent-light">{statusBot.reputation.level}</span>
                      <span className="text-icarus-muted"> · {statusBot.reputation.xp} XP · {statusBot.reputation.multiplier}x</span>
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold text-icarus-muted uppercase tracking-wider mb-3">Propostas Recentes</h2>
        <div className="space-y-3">
          {proposals.length === 0 && (
            <p className="text-icarus-muted text-sm">Nenhuma proposta ainda.</p>
          )}
          {proposals.map(p => (
            <ProposalRow key={p.id} proposal={p} />
          ))}
        </div>
      </div>

      <p className="text-center text-xs text-icarus-muted mt-8">
        Última atualização: {status.updatedAt ? new Date(status.updatedAt).toLocaleString() : '—'}
      </p>
    </div>
  );
}
