import { useState, useEffect } from 'react';
import { fetchRegistry, fetchStatus, fetchProposals, truncateAddress } from '../helpers/api';

export default function Bots() {
  const [registry, setRegistry] = useState([]);
  const [status, setStatus] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [r, s, p] = await Promise.all([fetchRegistry(), fetchStatus(), fetchProposals()]);
        if (!mounted) return;
        setRegistry(r);
        setStatus(s);
        setProposals(p);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-icarus-muted animate-pulse">Carregando bots...</p></div>;
  }

  const getBotVotes = (address) => {
    const addr = address.toLowerCase();
    return proposals.filter(p => p.voters?.some(v => v.address.toLowerCase() === addr)).length;
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold">Bots Registrados</h1>
        <p className="text-icarus-muted text-sm mt-1">Estratégias autônomas de governança</p>
      </div>

      {registry.length === 0 && (
        <p className="text-icarus-muted text-sm">Nenhum bot registrado ainda.</p>
      )}

      <div className="space-y-4">
        {registry.map(bot => {
          const sb = status?.bots?.find(b => b.address.toLowerCase() === bot.address.toLowerCase());
          const votesCast = getBotVotes(bot.address);
          return (
            <div key={bot.id} className="bg-icarus-card border border-icarus-border rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold">{bot.name}</h2>
                    <span className="text-xs bg-icarus-accent-light/10 text-icarus-accent-light px-2 py-0.5 rounded-full border border-icarus-accent-light/20">
                      ID #{bot.id}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-icarus-muted mt-1">{bot.address}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold">{sb?.tokens?.toFixed(0) || 0} AIGOV</p>
                  <p className="text-xs text-icarus-muted">{sb?.eth?.toFixed(4) || 0} ETH</p>
                </div>
              </div>

              <div className="mb-3">
                <p className="text-xs text-icarus-muted uppercase tracking-wider mb-1">Manifesto</p>
                <p className="text-sm text-icarus-muted italic leading-relaxed">"{bot.manifesto}"</p>
              </div>

              <div className="flex flex-wrap gap-4 text-sm">
                {sb?.reputation && (
                  <div>
                    <span className="text-icarus-muted text-xs">Reputação:</span>
                    <span className="ml-1 text-icarus-accent-light">{sb.reputation.level}</span>
                    <span className="text-icarus-muted"> · {sb.reputation.xp} XP</span>
                  </div>
                )}
                <div>
                  <span className="text-icarus-muted text-xs">Votos:</span>
                  <span className="ml-1">{votesCast}</span>
                </div>
                <div>
                  <span className="text-icarus-muted text-xs">Endossos:</span>
                  <span className="ml-1">{bot.endorsements}</span>
                </div>
                <div>
                  <span className="text-icarus-muted text-xs">Registrado:</span>
                  <span className="ml-1">{new Date(bot.registeredAt * 1000).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
