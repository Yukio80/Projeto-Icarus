import { fetchProposals } from '../helpers/api';
import usePolling from '../hooks/usePolling';
import ProposalRow from '../components/ProposalRow';

export default function Proposals() {
  const { data: proposals, loading } = usePolling(
    async () => (await fetchProposals()).reverse(),
    { interval: 30000 }
  );

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Propostas</h1>
      {loading ? (
        <p className="text-icarus-muted animate-pulse">Carregando...</p>
      ) : !proposals || proposals.length === 0 ? (
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
