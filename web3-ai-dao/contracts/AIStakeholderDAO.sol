// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IReputation {
    function getVotingMultiplier(address user) external view returns (uint256);
    function recordVote(address user) external;
}

contract AIStakeholderDAO is ReentrancyGuard {
    IERC20 public governanceToken;
    address public treasury;
    uint256 public proposalCount;
    uint256 public votingPeriod = 3 days;
    uint256 public quorum = 10_000 * 10 ** 18;
    IReputation public reputationNFT;

    struct Proposal {
        uint256 id;
        string description;
        uint256 amount;
        address payable recipient;
        uint256 createdAt;
        uint256 forVotes;
        uint256 againstVotes;
        bool executed;
        bool exists;
    }

    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(address => uint256) public delegates;

    event ProposalCreated(uint256 indexed id, string description, uint256 amount, address recipient);
    event Voted(uint256 indexed id, address indexed voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id);

    modifier proposalExists(uint256 proposalId) {
        require(proposals[proposalId].exists, "Proposal does not exist");
        _;
    }

    constructor(address _token, address _treasury, address _reputationNFT) {
        require(_token != address(0), "Invalid token address");
        require(_treasury != address(0), "Invalid treasury address");
        governanceToken = IERC20(_token);
        treasury = _treasury;
        reputationNFT = IReputation(_reputationNFT);
    }

    function createProposal(
        string calldata description,
        uint256 amount,
        address payable recipient
    ) external {
        require(bytes(description).length > 0, "Description required");
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be > 0");

        proposalCount++;
        proposals[proposalCount] = Proposal({
            id: proposalCount,
            description: description,
            amount: amount,
            recipient: recipient,
            createdAt: block.timestamp,
            forVotes: 0,
            againstVotes: 0,
            executed: false,
            exists: true
        });

        emit ProposalCreated(proposalCount, description, amount, recipient);
    }

    function vote(uint256 proposalId, bool support) external proposalExists(proposalId) {
        Proposal storage prop = proposals[proposalId];
        require(block.timestamp < prop.createdAt + votingPeriod, "Voting period ended");
        require(!hasVoted[proposalId][msg.sender], "Already voted");

        uint256 weight = getVotingPower(msg.sender);
        require(weight > 0, "No voting power");

        hasVoted[proposalId][msg.sender] = true;

        if (support) {
            prop.forVotes += weight;
        } else {
            prop.againstVotes += weight;
        }

        if (address(reputationNFT) != address(0)) {
            (bool success,) = address(reputationNFT).call(
                abi.encodeWithSelector(IReputation.recordVote.selector, msg.sender)
            );
            success; // suppress unused warning
        }

        emit Voted(proposalId, msg.sender, support, weight);
    }

    function executeProposal(uint256 proposalId) external proposalExists(proposalId) nonReentrant {
        Proposal storage prop = proposals[proposalId];
        require(!prop.executed, "Already executed");
        require(block.timestamp >= prop.createdAt + votingPeriod, "Voting period not ended");
        require(prop.forVotes > prop.againstVotes, "Proposal rejected");
        require(prop.forVotes >= quorum, "Quorum not reached");

        prop.executed = true;
        require(
            governanceToken.transferFrom(treasury, prop.recipient, prop.amount),
            "Transfer failed"
        );

        emit ProposalExecuted(proposalId);
    }

    function getVotingPower(address voter) public view returns (uint256) {
        uint256 balance = governanceToken.balanceOf(voter);
        uint256 delegated = delegates[voter];
        uint256 base = balance + delegated;
        if (address(reputationNFT) != address(0)) {
            return base * reputationNFT.getVotingMultiplier(voter);
        }
        return base;
    }

    function delegatePower(address to) external {
        require(to != address(0), "Invalid delegate");
        uint256 power = governanceToken.balanceOf(msg.sender);
        delegates[to] += power;
    }

    function getProposal(uint256 proposalId)
        external
        view
        returns (Proposal memory)
    {
        require(proposals[proposalId].exists, "Proposal does not exist");
        return proposals[proposalId];
    }

    function hasVotingPeriodEnded(uint256 proposalId) external view returns (bool) {
        require(proposals[proposalId].exists, "Proposal does not exist");
        return block.timestamp >= proposals[proposalId].createdAt + votingPeriod;
    }
}
