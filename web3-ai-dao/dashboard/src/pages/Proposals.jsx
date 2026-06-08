import { useState, useEffect } from 'react';
import { fetchProposals } from '../helpers/api';
import ProposalRow from '../components/ProposalRow';

export default function Proposals() {
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const p = await fetchProposals();
        if (mounted) setProposals(p.reverse());
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

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Propostas</h1>
      {loading ? (
        <p className="text-icarus-muted animate-pulse">Carregando...</p>
      ) : proposals.length === 0 ? (
        <p className="text-icarus-muted">Nenhuma proposta encontrada.</p>
      ) : (
        <div className="space-y-3">
          {proposals.map(p => (
            <ProposalRow key={p.id} proposal={p} />
          ))}
        </div>
      )}
    </div>
  );
}
