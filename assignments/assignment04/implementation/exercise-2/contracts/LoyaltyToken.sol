// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title LoyaltyToken
 * @notice ERC-20 loyalty points token for a business rewards programme.
 *         The owner (business admin) mints points to reward customers.
 *         Customers can view balances, transfer points to other wallets,
 *         and burn (redeem) their own points.
 *
 * Design choices
 * ──────────────
 * • Inherits OpenZeppelin ERC20 and Ownable for standard compliance and
 *   well-audited access control.  Rolling our own would add risk with no gain.
 * • No initial supply: points are minted on demand as customers earn rewards,
 *   which mirrors how loyalty programmes work in practice.
 * • Standard 18 decimals retained for ERC-20 compatibility.  The frontend
 *   displays whole "points" by dividing by 1e18.
 * • burn() lets users spend/redeem their own points.
 * • burnFrom() allows an approved contract (e.g. a future redemption contract)
 *   to burn on behalf of a user — follows the standard allowance pattern.
 * • No admin ability to burn other users' tokens: the owner can mint but
 *   cannot confiscate user balances.  This is an explicit trust boundary.
 *
 * Security considerations
 * ───────────────────────
 * • Only owner can inflate supply (mint).
 * • Transfer/approval logic is inherited from the OZ audited implementation.
 * • Overflow: Solidity 0.8.x and OZ both guard against overflow.
 * • Zero-address checks: _mint/_burn in OZ already reject address(0); the
 *   explicit require here makes the intent visible at the call site.
 */
contract LoyaltyToken is ERC20, Ownable {

    // ─── Events ──────────────────────────────────────────────────────────────

    /// Emitted when the admin rewards a customer with new points.
    event TokensMinted(address indexed to, uint256 amount);

    /// Emitted when a user burns (redeems) their own points.
    event TokensBurned(address indexed from, uint256 amount);

    // ─── Constructor ─────────────────────────────────────────────────────────

    /// @param name_   Human-readable token name (e.g. "LoyaltyPoints").
    /// @param symbol_ Ticker symbol (e.g. "LPT").
    constructor(string memory name_, string memory symbol_)
        ERC20(name_, symbol_)
        Ownable(msg.sender)
    {}

    // ─── Admin functions ──────────────────────────────────────────────────────

    /**
     * @notice Mint `amount` points (in wei units) to customer `to`.
     * @dev    Only the owner (business) may call this.
     * @param to     Recipient wallet — the customer being rewarded.
     * @param amount Token amount in the smallest unit (divide by 1e18 for display).
     */
    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "LoyaltyToken: mint to zero address");
        require(amount > 0,       "LoyaltyToken: amount must be > 0");
        _mint(to, amount);
        emit TokensMinted(to, amount);
    }

    // ─── User functions ───────────────────────────────────────────────────────

    /**
     * @notice Burn (redeem) `amount` of the caller's own points.
     * @dev    Caller must hold at least `amount` tokens; OZ _burn enforces this.
     */
    function burn(uint256 amount) external {
        require(amount > 0, "LoyaltyToken: amount must be > 0");
        _burn(msg.sender, amount);
        emit TokensBurned(msg.sender, amount);
    }

    /**
     * @notice Burn `amount` from `from` using the caller's approved allowance.
     * @dev    Follows the same pattern as ERC20's transferFrom: caller needs
     *         prior approval via approve().  Intended for redemption contracts.
     */
    function burnFrom(address from, uint256 amount) external {
        require(amount > 0, "LoyaltyToken: amount must be > 0");
        _spendAllowance(from, msg.sender, amount);
        _burn(from, amount);
        emit TokensBurned(from, amount);
    }
}
