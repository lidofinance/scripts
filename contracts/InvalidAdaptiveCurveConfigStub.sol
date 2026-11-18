// SPDX-License-Identifier: MIT
pragma solidity 0.8.6;

/// @dev Test-only config: ABI-compatible, but violates canonical parameter bounds.
contract InvalidAdaptiveCurveConfigStub {
    function getCurveParams() external pure returns (int256, int256, int256, int256, int256, int256, uint256) {
        return (0, 0, 0, 0, 0, 0, 0);
    }
}
