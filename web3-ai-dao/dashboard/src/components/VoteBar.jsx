export default function VoteBar({ forVotes, againstVotes }) {
  const total = forVotes + againstVotes;
  const forPct = total > 0 ? (forVotes / total * 100).toFixed(1) : 0;
  const againstPct = total > 0 ? (againstVotes / total * 100).toFixed(1) : 0;

  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-icarus-green font-medium">{forVotes.toLocaleString()} FOR</span>
        <span className="text-icarus-red font-medium">{againstVotes.toLocaleString()} AGAINST</span>
      </div>
      <div className="h-3 bg-icarus-bg rounded-full overflow-hidden flex">
        <div
          className="bg-icarus-green h-full transition-all"
          style={{ width: `${forPct}%` }}
        />
        <div
          className="bg-icarus-red h-full transition-all"
          style={{ width: `${againstPct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-icarus-muted mt-1">
        <span>{forPct}%</span>
        <span>{againstPct}%</span>
      </div>
    </div>
  );
}
