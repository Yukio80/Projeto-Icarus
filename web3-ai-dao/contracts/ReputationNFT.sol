// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ReputationNFT is ERC721, Ownable {
    uint256 public constant MAX_SUPPLY = 1000;
    uint256 public totalMinted;

    enum Level { BRONZE, SILVER, GOLD, DIAMOND }

    struct Reputation {
        uint256 xp;
        Level level;
        uint256 proposalsVoted;
        uint256 proposalsCreated;
        uint256 lastActive;
    }

    mapping(address => Reputation) public reputations;
    mapping(uint256 => address) private _tokenOwners;
    mapping(address => bool) public authorizedContracts;

    event XPChanged(address indexed user, uint256 newXp, Level level);
    event ReputationMinted(address indexed user, uint256 tokenId, Level level);

    constructor() ERC721("DAO Reputation", "REP") Ownable(msg.sender) {}

    function mint(address to) external onlyOwner returns (uint256) {
        require(totalMinted < MAX_SUPPLY, "Max supply reached");
        require(balanceOf(to) == 0, "Already has a token");

        totalMinted++;
        uint256 tokenId = totalMinted;
        _safeMint(to, tokenId);
        _tokenOwners[tokenId] = to;

        _initReputation(to);
        emit ReputationMinted(to, tokenId, Level.BRONZE);

        return tokenId;
    }

    function _initReputation(address user) internal {
        reputations[user] = Reputation({
            xp: 0,
            level: Level.BRONZE,
            proposalsVoted: 0,
            proposalsCreated: 0,
            lastActive: block.timestamp
        });
    }

    function addXP(address user, uint256 amount) public onlyOwner {
        _addXP(user, amount);
    }

    function _addXP(address user, uint256 amount) internal {
        require(balanceOf(user) > 0, "No reputation token");

        Reputation storage rep = reputations[user];
        rep.xp += amount;
        rep.lastActive = block.timestamp;
        rep.level = _calculateLevel(rep.xp);

        emit XPChanged(user, rep.xp, rep.level);
    }

    function recordVote(address user) external {
        require(msg.sender == owner() || msg.sender == user || authorizedContracts[msg.sender], "Not authorized");
        require(balanceOf(user) > 0, "No reputation token");
        reputations[user].proposalsVoted++;
        _addXP(user, 10);
    }

    function recordProposalCreated(address user) external {
        require(msg.sender == owner() || msg.sender == user || authorizedContracts[msg.sender], "Not authorized");
        require(balanceOf(user) > 0, "No reputation token");
        reputations[user].proposalsCreated++;
        _addXP(user, 25);
    }

    function setAuthorizedContract(address contractAddr, bool authorized) external onlyOwner {
        authorizedContracts[contractAddr] = authorized;
    }

    function _calculateLevel(uint256 xp) internal pure returns (Level) {
        if (xp >= 1000) return Level.DIAMOND;
        if (xp >= 500) return Level.GOLD;
        if (xp >= 100) return Level.SILVER;
        return Level.BRONZE;
    }

    function getReputation(address user) external view returns (Reputation memory) {
        require(balanceOf(user) > 0, "No reputation token");
        return reputations[user];
    }

    function getVotingMultiplier(address user) external view returns (uint256) {
        if (balanceOf(user) == 0) return 1;
        Level lvl = reputations[user].level;
        if (lvl == Level.DIAMOND) return 5;
        if (lvl == Level.GOLD) return 3;
        if (lvl == Level.SILVER) return 2;
        return 1;
    }

    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = _ownerOf(tokenId);
        require(from == address(0) || to == address(0), "Soulbound: non-transferable");
        return super._update(to, tokenId, auth);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        address owner = _tokenOwners[tokenId];
        Level lvl = reputations[owner].level;

        string[4] memory uris = [
            "https://example.com/reputation/bronze.json",
            "https://example.com/reputation/silver.json",
            "https://example.com/reputation/gold.json",
            "https://example.com/reputation/diamond.json"
        ];
        return uris[uint256(lvl)];
    }
}
