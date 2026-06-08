import { useParams, Link } from 'react-router-dom';
import { fetchProposals, fetchVotes, truncateAddress, proposalStatus } from '../helpers/api';
import usePolling from '../hooks/usePolling';
import VoteBar from '../components/VoteBar';

export default function ProposalDetail() {
  const { id } = useParams();
  const { data, loading } = usePolling(
    async () => {
      const [proposals, allVotes] = await Promise.all([fetchProposals(), fetchVotes()]);
      return {
        proposal: proposals.find(x => x.id === parseInt(id)),
        votes: allVotes.filter(x => x.proposalId === parseInt(id)),
      };
    },
    { interval: 15000, deps: [id] }
  );

  const proposal = data?.proposal;

  if (loading) {
    return <p className="text-icarus-muted animate-pulse mt-8">Carregando...</p>;
  }

  if (!proposal) {
    return (
      <div className="text-center mt-12">
        <p className="text-icarus-muted">Proposta #{id} não encontrada.</p>
        <Link to="/proposals" className="text-icarus-accent text-sm mt-2 inline-block hover:underline">
          ← Voltar
        </Link>
      </div>
    );
  }

  const status = proposalStatus(proposal);

  return (
    <div>
      <Link to="/proposals" className="text-icarus-accent text-sm hover:underline">← Propostas</Link>

      <div className="bg-icarus-card border border-icarus-border rounded-xl p-6 mt-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-icarus-muted text-sm font-mono">#{proposal.id}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${status.color} border-current`}>
            {status.label}
          </span>
        </div>

        <h1 className="text-lg font-bold mb-2">{proposal.description}</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 text-sm">
          <div>
            <p className="text-icarus-muted text-xs">Valor</p>
            <p className="font-medium">{proposal.amount} AIGOV</p>
          </div>
          <div>
            <p className="text-icarus-muted text-xs">Destinatário</p>
            <p className="font-mono text-xs">{truncateAddress(proposal.recipient)}</p>
          </div>
          <div>
            <p className="text-icarus-muted text-xs">Criada em</p>
            <p className="font-medium">{new Date(proposal.createdAt * 1000).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-icarus-muted text-xs">Status</p>
            <p className={`font-medium ${status.color}`}>{status.label}</p>
          </div>
        </div>

        <div className="mt-6">
          <h2 className="text-sm font-semibold text-icarus-muted uppercase tracking-wider mb-3">Votação</h2>
          <VoteBar forVotes={proposal.forVotes} againstVotes={proposal.againstVotes} />

          {proposal.executed && (
            <p className="text-icarus-green text-sm mt-3 font-medium">✓ Proposta executada</p>
          )}
        </div>

        {(proposal.voteEvents && proposal.voteEvents.length > 0) && (
          <div className="mt-6">
            <h2 className="text-sm font-semibold text-icarus-muted uppercase tracking-wider mb-3">
              Votos ({proposal.voteEvents.length})
            </h2>
            <div className="space-y-2">
              {proposal.voteEvents.map((v, i) => (
                <div key={i} className="flex items-center justify-between bg-icarus-bg rounded-lg px-3 py-2 text-sm">
                  <span className="font-mono text-xs">{truncateAddress(v.voter)}</span>
                  <div className="flex items-center gap-3">
                    <span className={v.support ? 'text-icarus-green' : 'text-icarus-red'}>
                      {v.support ? 'FOR' : 'AGAINST'}
                    </span>
                    <span className="text-icarus-muted">{v.weight} votos</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
