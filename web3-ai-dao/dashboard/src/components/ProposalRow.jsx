import { Link } from 'react-router-dom';
import { truncateAddress, proposalStatus, timeAgo } from '../helpers/api';

export default function ProposalRow({ proposal }) {
  const status = proposalStatus(proposal);
  const pct = proposal.forVotes + proposal.againstVotes > 0
    ? (proposal.forVotes / (proposal.forVotes + proposal.againstVotes) * 100).toFixed(0)
    : 0;

  return (
    <Link
      to={`/proposal/${proposal.id}`}
      className="block bg-icarus-card border border-icarus-border rounded-xl p-4 hover:border-icarus-accent transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-icarus-muted text-sm font-mono">#{proposal.id}</span>
            <span className={`text-xs font-medium ${status.color}`}>{status.label}</span>
          </div>
          <p className="text-sm font-medium mt-1 truncate">{proposal.description}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-icarus-muted">
            <span>{proposal.amount} AIGOV</span>
            <span>→ {truncateAddress(proposal.recipient)}</span>
            <span>{timeAgo(proposal.createdAt)}</span>
          </div>
        </div>
        <div className="text-right ml-4">
          <p className="text-lg font-bold text-icarus-green">{proposal.forVotes.toLocaleString()}</p>
          <p className="text-xs text-icarus-muted">FOR ({pct}%)</p>
        </div>
      </div>
      <div className="mt-3 h-1.5 bg-icarus-bg rounded-full overflow-hidden">
        <div
          className="h-full bg-icarus-green rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </Link>
  );
}
