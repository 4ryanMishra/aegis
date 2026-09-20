// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MockOracleFeeds
/// @notice Deterministic mock contracts providing realistic interfaces for testing and simulation.

// --- Chainlink Aggregator Mock ---
interface AggregatorV3Interface {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function version() external view returns (uint256);
    function getRoundData(uint80 _roundId) external view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
    function latestRoundData() external view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract MockChainlinkFeed is AggregatorV3Interface {
    uint8 public immutable override decimals;
    int256 public latestAnswer;
    uint256 public latestTimestamp;
    uint80 public latestRound;

    constructor(uint8 _decimals, int256 _initialPrice) {
        decimals = _decimals;
        latestAnswer = _initialPrice;
        latestTimestamp = block.timestamp;
        latestRound = 1;
    }

    function setPrice(int256 _price, uint256 _timestamp) external {
        latestAnswer = _price;
        latestTimestamp = _timestamp;
        latestRound++;
    }

    function description() external pure override returns (string memory) {
        return "Mock Chainlink Aggregator";
    }

    function version() external pure override returns (uint256) {
        return 4;
    }

    function getRoundData(uint80 _roundId) external view override returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound) {
        return (_roundId, latestAnswer, latestTimestamp, latestTimestamp, _roundId);
    }

    function latestRoundData() external view override returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound) {
        return (latestRound, latestAnswer, latestTimestamp, latestTimestamp, latestRound);
    }
}

// --- Pyth Network Mock ---
library PythStructs {
    struct Price {
        int64 price;
        uint64 conf;
        int32 expo;
        uint256 publishTime;
    }
}

interface IPyth {
    function getPriceUnsafe(bytes32 id) external view returns (PythStructs.Price memory price);
    function getPriceNoOlderThan(bytes32 id, uint256 age) external view returns (PythStructs.Price memory price);
}

contract MockPythFeed is IPyth {
    mapping(bytes32 => PythStructs.Price) public prices;

    function setPrice(bytes32 id, int64 price, uint64 conf, int32 expo, uint256 publishTime) external {
        prices[id] = PythStructs.Price({
            price: price,
            conf: conf,
            expo: expo,
            publishTime: publishTime
        });
    }

    function getPriceUnsafe(bytes32 id) external view override returns (PythStructs.Price memory price) {
        price = prices[id];
        require(price.publishTime > 0, "No price for feed");
        return price;
    }

    function getPriceNoOlderThan(bytes32 id, uint256 age) external view override returns (PythStructs.Price memory price) {
        price = prices[id];
        require(price.publishTime > 0, "No price for feed");
        require(block.timestamp - price.publishTime <= age, "Price is too old");
        return price;
    }
}

// --- Chronicle Scribe Mock ---
interface IChronicleScribe {
    function read() external view returns (uint256 val, uint256 age);
    function latestAnswer() external view returns (int256);
}

contract MockChronicleFeed is IChronicleScribe {
    uint256 public price;
    uint256 public lastUpdated;

    constructor(uint256 _price) {
        price = _price;
        lastUpdated = block.timestamp;
    }

    function setPrice(uint256 _price, uint256 _lastUpdated) external {
        price = _price;
        lastUpdated = _lastUpdated;
    }

    function read() external view override returns (uint256 val, uint256 age) {
        require(price > 0, "No price");
        uint256 calculatedAge = block.timestamp >= lastUpdated ? block.timestamp - lastUpdated : 0;
        return (price, calculatedAge);
    }

    function latestAnswer() external view override returns (int256) {
        return int256(price);
    }
}

// --- RedStone Oracle Mock ---
interface IRedStoneFeed {
    function getValue() external view returns (uint256 price, uint256 timestamp);
}

contract MockRedStoneFeed is IRedStoneFeed {
    uint256 public price;
    uint256 public timestamp;

    constructor(uint256 _price) {
        price = _price;
        timestamp = block.timestamp;
    }

    function setPrice(uint256 _price, uint256 _timestamp) external {
        price = _price;
        timestamp = _timestamp;
    }

    function getValue() external view override returns (uint256, uint256) {
        return (price, timestamp);
    }
}

// --- Supra DORA Mock ---
interface ISupraRouter {
    function getSvalue(uint256 pairId) external view returns (uint256 round, int256 price, uint256 timestamp, uint256 decimals);
}

contract MockSupraFeed is ISupraRouter {
    mapping(uint256 => int256) public prices;
    mapping(uint256 => uint256) public timestamps;
    mapping(uint256 => uint256) public decimalMap;
    uint256 public currentRound = 1;

    function setPrice(uint256 pairId, int256 _price, uint256 _timestamp, uint256 _decimals) external {
        prices[pairId] = _price;
        timestamps[pairId] = _timestamp;
        decimalMap[pairId] = _decimals;
        currentRound++;
    }

    function getSvalue(uint256 pairId) external view override returns (uint256 round, int256 price, uint256 timestamp, uint256 decimals) {
        require(timestamps[pairId] > 0, "Pair not found");
        return (currentRound, prices[pairId], timestamps[pairId], decimalMap[pairId]);
    }
}

// --- API3 dAPI Mock ---
interface IAPI3Reader {
    function read() external view returns (int224 value, uint32 timestamp);
}

contract MockAPI3Feed is IAPI3Reader {
    int224 public price;
    uint32 public timestamp;

    constructor(int224 _price) {
        price = _price;
        timestamp = uint32(block.timestamp);
    }

    function setPrice(int224 _price, uint32 _timestamp) external {
        price = _price;
        timestamp = _timestamp;
    }

    function read() external view override returns (int224, uint32) {
        return (price, timestamp);
    }
}

// --- Multipli OSM Mock ---
contract MockMultipliOSM {
    uint256 public price;
    bool public hasPrice;
    uint256 public lastUpdated;

    constructor(uint256 _price) {
        price = _price;
        hasPrice = true;
        lastUpdated = block.timestamp;
    }

    function setPrice(uint256 _price, bool _hasPrice) external {
        price = _price;
        hasPrice = _hasPrice;
        lastUpdated = block.timestamp;
    }

    function readPrice() external view returns (uint256, bool) {
        return (price, hasPrice);
    }
}
