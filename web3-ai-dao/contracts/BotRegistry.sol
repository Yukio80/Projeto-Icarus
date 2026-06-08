// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

contract BotRegistry {
    struct BotInfo {
        uint256 id;
        address botAddress;
        string name;
        string manifesto;
        string metadataURI;
        uint256 registeredAt;
        uint256 endorsementCount;
        bool active;
    }

    uint256 public botCount;
    mapping(uint256 => BotInfo) public bots;
    mapping(address => uint256) public addressToBotId;
    mapping(uint256 => mapping(address => bool)) public endorsedBy;

    event BotRegistered(
        uint256 indexed id,
        address indexed botAddress,
        string name,
        string manifesto
    );

    event BotEndorsed(uint256 indexed id, address indexed endorser);
    event BotDeactivated(uint256 indexed id);
    event BotUpdated(uint256 indexed id, string name, string manifesto);

    function registerBot(
        string calldata _name,
        string calldata _manifesto,
        string calldata _metadataURI
    ) external returns (uint256) {
        require(addressToBotId[msg.sender] == 0, "Already registered");
        require(bytes(_name).length > 0, "Name required");
        require(bytes(_manifesto).length > 0, "Manifesto required");

        botCount++;
        uint256 newId = botCount;

        bots[newId] = BotInfo({
            id: newId,
            botAddress: msg.sender,
            name: _name,
            manifesto: _manifesto,
            metadataURI: _metadataURI,
            registeredAt: block.timestamp,
            endorsementCount: 0,
            active: true
        });

        addressToBotId[msg.sender] = newId;

        emit BotRegistered(newId, msg.sender, _name, _manifesto);

        return newId;
    }

    function endorseBot(uint256 _botId) external {
        require(bots[_botId].active, "Bot not active");
        require(!endorsedBy[_botId][msg.sender], "Already endorsed");

        endorsedBy[_botId][msg.sender] = true;
        bots[_botId].endorsementCount++;

        emit BotEndorsed(_botId, msg.sender);
    }

    function updateBot(
        string calldata _name,
        string calldata _manifesto,
        string calldata _metadataURI
    ) external {
        uint256 id = addressToBotId[msg.sender];
        require(id != 0, "Not registered");
        require(bytes(_name).length > 0, "Name required");
        require(bytes(_manifesto).length > 0, "Manifesto required");

        bots[id].name = _name;
        bots[id].manifesto = _manifesto;
        bots[id].metadataURI = _metadataURI;

        emit BotUpdated(id, _name, _manifesto);
    }

    function deactivateBot(uint256 _botId) external {
        require(
            msg.sender == bots[_botId].botAddress,
            "Only bot owner"
        );
        require(bots[_botId].active, "Already inactive");

        bots[_botId].active = false;

        emit BotDeactivated(_botId);
    }

    function getActiveBots() external view returns (BotInfo[] memory) {
        uint256 count = 0;
        for (uint256 i = 1; i <= botCount; i++) {
            if (bots[i].active) count++;
        }

        BotInfo[] memory result = new BotInfo[](count);
        uint256 idx = 0;
        for (uint256 i = 1; i <= botCount; i++) {
            if (bots[i].active) {
                result[idx] = bots[i];
                idx++;
            }
        }
        return result;
    }

    function getBotByAddress(address _addr) external view returns (BotInfo memory) {
        uint256 id = addressToBotId[_addr];
        require(id != 0, "Not registered");
        return bots[id];
    }
}
