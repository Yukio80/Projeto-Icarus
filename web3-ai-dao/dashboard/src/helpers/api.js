const API_BASE = '/data';

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchProposals() {
  const data = await fetchJSON('/proposals.json');
  return data.proposals || [];
}

export async function fetchVotes() {
  const data = await fetchJSON('/votes.json');
  return data.votes || [];
}

export async function fetchStatus() {
  return fetchJSON('/status.json');
}

export async function fetchRegistry() {
  const data = await fetchJSON('/registry.json');
  return data.bots || [];
}

export function truncateAddress(addr) {
  if (!addr) return '';
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export function timeAgo(timestamp) {
  const now = Math.floor(Date.now() / 1000);
  const diff = now - timestamp;
  if (diff < 60) return `${diff}s atrás`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

export function proposalStatus(proposal) {
  if (proposal.executed) return { label: 'Executada', color: 'text-icarus-green' };
  const now = Math.floor(Date.now() / 1000);
  const votingEnd = proposal.createdAt + 259200; // 3 days
  if (now >= votingEnd) return { label: 'Encerrada', color: 'text-icarus-muted' };
  return { label: 'Votando', color: 'text-icarus-accent-light' };
}
