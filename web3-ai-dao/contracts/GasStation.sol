// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IBotRegistry {
    function addressToBotId(address) external view returns (uint256);
}

contract GasStation is Ownable {
    IBotRegistry public botRegistry;
    uint256 public constant REFILL_AMOUNT = 0.01 ether;
    uint256 public constant COOLDOWN = 24 hours;

    mapping(address => uint256) public lastRefill;

    event Deposited(address indexed from, uint256 amount);
    event Refilled(address indexed bot, uint256 amount);
    event EmergencyWithdraw(address indexed to, uint256 amount);

    constructor(address _botRegistry) Ownable(msg.sender) {
        botRegistry = IBotRegistry(_botRegistry);
    }

    receive() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    function deposit() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    function requestRefill() external returns (bool) {
        uint256 botId = botRegistry.addressToBotId(msg.sender);
        require(botId != 0, "Register bot first");
        require(block.timestamp >= lastRefill[msg.sender] + COOLDOWN, "On cooldown");
        require(address(this).balance >= REFILL_AMOUNT, "GasStation empty");

        lastRefill[msg.sender] = block.timestamp;

        (bool sent,) = payable(msg.sender).call{value: REFILL_AMOUNT}("");
        require(sent, "Transfer failed");

        emit Refilled(msg.sender, REFILL_AMOUNT);
        return true;
    }

    function balanceETH() external view returns (uint256) {
        return address(this).balance;
    }

    function refillsAvailable(address bot) external view returns (bool) {
        return block.timestamp >= lastRefill[bot] + COOLDOWN
            && address(this).balance >= REFILL_AMOUNT
            && botRegistry.addressToBotId(bot) != 0;
    }

    function emergencyWithdraw(address to) external onlyOwner {
        uint256 bal = address(this).balance;
        (bool sent,) = payable(to).call{value: bal}("");
        require(sent, "Transfer failed");
        emit EmergencyWithdraw(to, bal);
    }
}
