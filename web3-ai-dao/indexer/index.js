const { ethers } = require('ethers');
const dotenv = require('dotenv');
const fs = require('fs');
const path = require('path');
const http = require('http');

process.on('unhandledRejection', (e) => {
  console.error(`[FATAL] Unhandled rejection: ${e.message}`);
});

dotenv.config({ path: path.join(__dirname, '..', '.env') });

const RPC_URL = process.env.RPC_URL;
const DAO_ADDRESS = process.env.DAO_ADDRESS;
const TOKEN_ADDRESS = process.env.TOKEN_ADDRESS;
const REPUTATION_NFT_ADDRESS = process.env.REPUTATION_NFT_ADDRESS || '';
const BOT_REGISTRY_ADDRESS = process.env.BOT_REGISTRY_ADDRESS || '';
const BOT_ADDRESSES = [
  process.env.CONSERVATIVE_ADDRESS || '',
  process.env.LIBERAL_ADDRESS || '',
  process.env.MARXIST_ADDRESS || '',
].filter(Boolean);
const PORT = parseInt(process.env.PORT || '3456');
const POLL_INTERVAL = parseInt(process.env.POLL_INTERVAL || '30') * 1000;

const STATE_FILE = path.join(__dirname, 'state.json');
const DATA_DIR = path.join(__dirname, '..', 'dashboard', 'public', 'data');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const DAO_ABI = [
  "event ProposalCreated(uint256 indexed id, string description, uint256 amount, address recipient)",
  "event Voted(uint256 indexed id, address indexed voter, bool support, uint256 weight)",
  "event ProposalExecuted(uint256 indexed id)",
  "function proposals(uint256) view returns (uint256 id, string description, uint256 amount, address payable recipient, uint256 createdAt, uint256 forVotes, uint256 againstVotes, bool executed, bool exists)",
  "function proposalCount() view returns (uint256)",
  "function hasVoted(uint256, address) view returns (bool)",
  "function votingPeriod() view returns (uint256)",
  "function getVotingPower(address) view returns (uint256)",
];

const TOKEN_ABI = [
  "function balanceOf(address) view returns (uint256)",
  "function totalSupply() view returns (uint256)",
];

const REPUTATION_ABI = [
  "function getReputation(address) view returns (uint256 xp, uint8 level, uint256 proposalsVoted, uint256 proposalsCreated, uint256 lastActive)",
  "function getVotingMultiplier(address) view returns (uint256)",
  "function balanceOf(address) view returns (uint256)",
];

const REGISTRY_ABI = [
  "function botCount() view returns (uint256)",
  "function getActiveBots() view returns (tuple(uint256 id, address botAddress, string name, string manifesto, string metadataURI, uint256 registeredAt, uint256 endorsementCount, bool active)[])",
  "function getBotByAddress(address) view returns (tuple(uint256 id, address botAddress, string name, string manifesto, string metadataURI, uint256 registeredAt, uint256 endorsementCount, bool active))",
  "function endorseBot(uint256) external",
];

let provider, dao, token, reputation, registry;
let state = { lastBlock: 0, proposals: [], votes: [] };
let cachedData = { proposals: [], votes: [], status: {} };

function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    }
  } catch (e) {
    console.error(`State load error: ${e.message}`);
  }
}

function saveState() {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  } catch (e) {
    console.error(`State save error: ${e.message}`);
  }
}

function writeJSON(filename, data) {
  const filepath = path.join(DATA_DIR, filename);
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
  console.log(`  Written ${filename}`);
}

async function getTokenBalance(address) {
  try {
    const bal = await token.balanceOf(address);
    return Number(ethers.formatUnits(bal, 18));
  } catch { return 0; }
}

async function getReputation(address) {
  if (!reputation) return null;
  try {
    const bal = await reputation.balanceOf(address);
    if (bal === 0n) return null;
    const rep = await reputation.getReputation(address);
    const mult = await reputation.getVotingMultiplier(address);
    const levels = ['BRONZE', 'SILVER', 'GOLD', 'DIAMOND'];
    return {
      xp: Number(rep.xp),
      level: levels[Number(rep.level)] || 'UNKNOWN',
      voted: Number(rep.proposalsVoted),
      created: Number(rep.proposalsCreated),
      multiplier: Number(mult),
    };
  } catch { return null; }
}

async function fetchProposals() {
  const count = Number(await dao.proposalCount());
  const proposals = [];
  for (let pid = 1; pid <= count; pid++) {
    const p = await dao.proposals(pid);
    if (!p.exists) continue;
    const voters = [];
    for (const addr of BOT_ADDRESSES) {
      const voted = await dao.hasVoted(pid, addr);
      if (voted) {
        const power = await dao.getVotingPower(addr);
        voters.push({
          address: addr,
          votingPower: Number(ethers.formatUnits(power, 18)),
        });
      }
    }
    proposals.push({
      id: Number(p.id),
      description: p.description,
      amount: ethers.formatUnits(p.amount, 18),
      recipient: p.recipient,
      createdAt: Number(p.createdAt),
      forVotes: Number(ethers.formatUnits(p.forVotes, 18)),
      againstVotes: Number(ethers.formatUnits(p.againstVotes, 18)),
      executed: p.executed,
      exists: p.exists,
      voters,
    });
  }
  return proposals;
}

async function fetchStatus(proposals) {
  const totalFor = proposals.reduce((s, p) => s + p.forVotes, 0);
  const totalAgainst = proposals.reduce((s, p) => s + p.againstVotes, 0);
  const executed = proposals.filter(p => p.executed).length;
  const treasuryBal = await getTokenBalance(DAO_ADDRESS);
  const bots = [];
  for (const addr of BOT_ADDRESSES) {
    bots.push({
      address: addr,
      eth: Number(ethers.formatEther(await provider.getBalance(addr))),
      tokens: await getTokenBalance(addr),
      reputation: await getReputation(addr),
    });
  }
  return {
    proposalCount: proposals.length,
    executedCount: executed,
    pendingCount: proposals.length - executed,
    totalForVotes: totalFor,
    totalAgainstVotes: totalAgainst,
    treasuryBalance: treasuryBal,
    tokenAddress: TOKEN_ADDRESS,
    daoAddress: DAO_ADDRESS,
    bots,
    updatedAt: new Date().toISOString(),
  };
}

async function fetchRegistry() {
  if (!registry) return [];
  try {
    const bots = await registry.getActiveBots();
    return bots.map(b => ({
      id: Number(b.id),
      address: b.botAddress,
      name: b.name,
      manifesto: b.manifesto,
      registeredAt: Number(b.registeredAt),
      endorsements: Number(b.endorsementCount),
      active: b.active,
    }));
  } catch { return []; }
}

function mergeEventsIntoProposals(proposals, events) {
  for (const event of events) {
    if (event.event === 'Voted') {
      const pid = Number(event.args.id);
      const existing = state.votes.find(v => v.proposalId === pid && v.voter === event.args.voter.toLowerCase());
      if (!existing) {
        state.votes.push({
          proposalId: pid,
          voter: event.args.voter.toLowerCase(),
          support: event.args.support,
          weight: Number(ethers.formatUnits(event.args.weight, 18)),
          timestamp: Math.floor(new Date(event.args.blockNumber ? event.blockNumber * 0 : Date.now()).getTime() / 1000),
          blockNumber: event.blockNumber,
          txHash: event.transactionHash,
        });
      }
    }
  }
}

async function pollEvents() {
  try {
    const latestBlock = await provider.getBlockNumber();
    const fromBlock = state.lastBlock || latestBlock - 10000;
    if (fromBlock >= latestBlock) return;

    console.log(`\n[${new Date().toISOString()}] Polling blocks ${fromBlock} → ${latestBlock}`);

    const allEvents = [];

    // Use smaller chunks for log queries to avoid Alchemy free tier limits
    const chunkSize = 9;
    for (let start = fromBlock; start <= latestBlock; start += chunkSize + 1) {
      const end = Math.min(start + chunkSize, latestBlock);
      const topicsList = [
        [ethers.id('ProposalCreated(uint256,string,uint256,address)'), 'Created'],
        [ethers.id('Voted(uint256,address,bool,uint256)'), 'Voted'],
        [ethers.id('ProposalExecuted(uint256)'), 'Executed'],
      ];
      for (const [topic, name] of topicsList) {
        try {
          const logs = await provider.getLogs({ address: DAO_ADDRESS, fromBlock: start, toBlock: end, topics: [topic] });
          for (const log of logs) {
            const parsed = dao.interface.parseLog(log);
            if (parsed) {
              allEvents.push({ event: parsed.name || name, args: parsed.args, blockNumber: log.blockNumber, transactionHash: log.transactionHash });
            }
          }
        } catch (e) {
          console.error(`  Log query ${name} [${start}..${end}] error: ${e.message.slice(0, 60)}`);
        }
      }
    }

    if (allEvents.length > 0) {
      console.log(`  Found ${allEvents.length} new events`);
      mergeEventsIntoProposals([], allEvents);
    }

    state.lastBlock = latestBlock;
    saveState();
    await rebuildCache();

  } catch (e) {
    console.error(`[${new Date().toISOString()}] Poll error: ${e.message}`);
  }
}

async function rebuildCache() {
  try {
    const proposals = await fetchProposals();
    const status = await fetchStatus(proposals);
    const registryBots = await fetchRegistry();

    // Merge registry data into status bots
    status.bots = status.bots.map(b => {
      const reg = registryBots.find(r => r.address.toLowerCase() === b.address.toLowerCase());
      return { ...b, registry: reg || null };
    });
    status.registryCount = registryBots.length;

    const proposalsWithVotes = proposals.map(p => {
      const relatedVotes = state.votes.filter(v => v.proposalId === p.id);
      return { ...p, voteEvents: relatedVotes };
    });

    cachedData = {
      proposals: proposalsWithVotes,
      votes: state.votes,
      status,
      registry: registryBots,
    };

    writeJSON('proposals.json', { updatedAt: status.updatedAt, proposals: proposalsWithVotes });
    writeJSON('votes.json', { updatedAt: status.updatedAt, votes: state.votes });
    writeJSON('status.json', status);
    writeJSON('registry.json', { updatedAt: status.updatedAt, bots: registryBots });

    console.log(`  ${proposals.length} proposals, ${state.votes.length} votes, ${registryBots.length} registered bots`);
  } catch (e) {
    console.error(`Rebuild error: ${e.message}`);
  }
}

function startHttpServer() {
  const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Content-Type', 'application/json');

    if (req.url === '/api/proposals') {
      res.end(JSON.stringify({ updatedAt: cachedData.status.updatedAt, proposals: cachedData.proposals }));
    } else if (req.url === '/api/votes') {
      res.end(JSON.stringify({ updatedAt: cachedData.status.updatedAt, votes: cachedData.votes }));
    } else if (req.url === '/api/status') {
      res.end(JSON.stringify(cachedData.status));
    } else if (req.url === '/api/registry') {
      res.end(JSON.stringify({ updatedAt: (cachedData.status && cachedData.status.updatedAt) || new Date().toISOString(), bots: cachedData.registry || [] }));
    } else {
      res.writeHead(404);
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  });

  server.on('error', (e) => {
    if (e.code === 'EADDRINUSE') {
      console.error(`Port ${PORT} in use — HTTP server not started`);
    } else {
      console.error(`Server error: ${e.message}`);
    }
  });

  server.listen(PORT, () => {
    console.log(`\nIndexer HTTP server running on http://localhost:${PORT}`);
    console.log(`  GET /api/proposals`);
    console.log(`  GET /api/votes`);
    console.log(`  GET /api/status`);
    console.log(`  GET /api/registry`);
  });
}

async function initialize() {
  provider = new ethers.JsonRpcProvider(RPC_URL);
  dao = new ethers.Contract(DAO_ADDRESS, DAO_ABI, provider);
  token = new ethers.Contract(TOKEN_ADDRESS, TOKEN_ABI, provider);
  if (REPUTATION_NFT_ADDRESS) {
    reputation = new ethers.Contract(REPUTATION_NFT_ADDRESS, REPUTATION_ABI, provider);
  }
  if (BOT_REGISTRY_ADDRESS) {
    registry = new ethers.Contract(BOT_REGISTRY_ADDRESS, REGISTRY_ABI, provider);
  }

  const network = await provider.getNetwork();
  console.log(`Connected: chainId=${network.chainId}`);
  console.log(`DAO: ${DAO_ADDRESS}`);
  console.log(`Registry: ${BOT_REGISTRY_ADDRESS || 'not set'}`);
  console.log(`Data dir: ${DATA_DIR}`);

  loadState();

  await rebuildCache();
  startHttpServer();
  await pollEvents();

  setInterval(() => pollEvents().catch(e => console.error(`Poll error: ${e.message}`)), POLL_INTERVAL);
}

initialize().catch(e => {
  console.error(`Fatal: ${e.message}`);
  process.exit(1);
});
