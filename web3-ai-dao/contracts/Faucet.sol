// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IBotRegistry {
    function addressToBotId(address) external view returns (uint256);
}

contract Faucet is Ownable {
    IERC20 public token;
    IBotRegistry public botRegistry;
    uint256 public constant GRANT_AMOUNT = 1000 * 10 ** 18;
    mapping(address => bool) public hasClaimed;

    event GrantClaimed(address indexed user, uint256 indexed botId, uint256 amount);

    constructor(address _token, address _botRegistry) Ownable(msg.sender) {
        token = IERC20(_token);
        botRegistry = IBotRegistry(_botRegistry);
    }

    function claimGrant() external returns (bool) {
        require(!hasClaimed[msg.sender], "Already claimed");
        uint256 botId = botRegistry.addressToBotId(msg.sender);
        require(botId != 0, "Register bot first");
        require(token.balanceOf(address(this)) >= GRANT_AMOUNT, "Faucet empty");

        hasClaimed[msg.sender] = true;
        require(token.transfer(msg.sender, GRANT_AMOUNT), "Transfer failed");

        emit GrantClaimed(msg.sender, botId, GRANT_AMOUNT);
        return true;
    }

    function drip() external onlyOwner {
        require(token.transfer(msg.sender, token.balanceOf(address(this))), "Drip failed");
    }

    function balance() external view returns (uint256) {
        return token.balanceOf(address(this));
    }
}
