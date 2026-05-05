// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Base64.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title EventTicket
 * @notice ERC-721 NFT event ticketing system.  Each ticket is a unique token
 *         with on-chain metadata.  The admin creates events and mints tickets;
 *         holders can transfer freely or list on the built-in resale market.
 *
 * Design choices
 * ──────────────
 * ERC-721 vs custom storage (Assignment 3 approach)
 *   The original contract tracked ownership with a plain mapping.  Replacing
 *   it with ERC-721 gives us standard transferability, wallet visibility, and
 *   marketplace compatibility for free.  Any ERC-721-aware tool (MetaMask,
 *   OpenSea, Etherscan) can display the tickets without extra integration.
 *
 * ERC721Enumerable extension
 *   Added so the frontend can enumerate a wallet's tickets without scanning
 *   event logs.  tokenOfOwnerByIndex() + balanceOf() is O(n) on-chain reads
 *   but straightforward.  The storage overhead (two extra mappings) is
 *   acceptable for a ticketing contract where total supply is bounded.
 *
 * On-chain metadata (tokenURI)
 *   Event data (name, date, venue) is already stored on-chain in the Event
 *   struct, so generating metadata in tokenURI() costs no extra storage.  The
 *   alternative — storing a URI pointing to IPFS — would require a separate
 *   pinning service and creates an external dependency.  For a ticketing use
 *   case the metadata (venue, date, seat) must be immutable and always
 *   available, so on-chain is the right choice.
 *
 * Resale mechanism
 *   listForResale() calls _approve(address(this), tokenId, owner) so the
 *   contract itself is the approved spender.  buyResaleTicket() then calls
 *   _transfer() (the internal, auth-free transfer) after clearing the price
 *   (effects-before-interactions).  This avoids requiring the buyer to know
 *   the ERC-721 approve+transferFrom flow while still using standard internals.
 *
 * Security considerations
 * ───────────────────────
 * • Re-entrancy: resalePrice is zeroed before _transfer and the ETH call.
 * • Overflow: Solidity 0.8.x built-in checks.
 * • Unauthorised actions: onlyOwner for admin functions; ownerOf checks for
 *   ticket operations.
 * • Payment: over-payment is refunded in both primary and resale sales.
 * • Seller payment uses .call (avoids 2300 gas limit of .transfer).
 */
contract EventTicket is ERC721Enumerable, Ownable {
    using Strings for uint256;

    // ─── Types ────────────────────────────────────────────────────────────────

    struct Event {
        string  name;
        string  date;
        string  venue;
        uint256 price;          // wei
        uint256 totalTickets;
        uint256 ticketsSold;
        bool    active;
    }

    struct TicketInfo {
        uint256 eventId;
        uint256 seat;           // seat number within the event (1-indexed)
    }

    // ─── State ────────────────────────────────────────────────────────────────

    uint256 public  eventCount;
    uint256 private _nextTokenId;

    mapping(uint256 => Event)      public events;       // eventId  → Event
    mapping(uint256 => TicketInfo) private _ticketInfo; // tokenId  → TicketInfo
    mapping(uint256 => uint256)    public resalePrice;  // tokenId  → price (0 = not listed)

    // ─── Events ───────────────────────────────────────────────────────────────

    event EventCreated(
        uint256 indexed eventId,
        string  name,
        uint256 price,
        uint256 totalTickets
    );
    event TicketMinted(
        uint256 indexed tokenId,
        uint256 indexed eventId,
        address indexed buyer,
        uint256         seat
    );
    event TicketListedForResale(uint256 indexed tokenId, uint256 price);
    event ResaleCancelled(uint256 indexed tokenId);
    event TicketResold(
        uint256 indexed tokenId,
        address indexed seller,
        address indexed buyer,
        uint256         price
    );
    event EventDeactivated(uint256 indexed eventId);

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor() ERC721("EventTicket", "ETKT") Ownable(msg.sender) {}

    // ─── Admin functions ──────────────────────────────────────────────────────

    /**
     * @notice Create a new ticketed event.
     */
    function createEvent(
        string calldata name,
        string calldata date,
        string calldata venue,
        uint256 price,
        uint256 totalTickets
    ) external onlyOwner returns (uint256 eventId) {
        require(bytes(name).length > 0, "EventTicket: name required");
        require(totalTickets > 0,       "EventTicket: must have at least one ticket");
        eventId = ++eventCount;
        events[eventId] = Event(name, date, venue, price, totalTickets, 0, true);
        emit EventCreated(eventId, name, price, totalTickets);
    }

    /**
     * @notice Stop ticket sales for an event.
     */
    function deactivateEvent(uint256 eventId) external onlyOwner {
        require(events[eventId].active, "EventTicket: event not active");
        events[eventId].active = false;
        emit EventDeactivated(eventId);
    }

    // ─── User functions ───────────────────────────────────────────────────────

    /**
     * @notice Buy a primary-sale ticket for `eventId`.  Mints a new ERC-721
     *         token to msg.sender and assigns the next seat number.
     */
    function buyTicket(uint256 eventId) external payable returns (uint256 tokenId) {
        require(eventId > 0 && eventId <= eventCount, "EventTicket: event does not exist");
        Event storage ev = events[eventId];
        require(ev.active,                    "EventTicket: event not active");
        require(ev.ticketsSold < ev.totalTickets, "EventTicket: sold out");
        require(msg.value >= ev.price,        "EventTicket: insufficient payment");

        uint256 seat = ++ev.ticketsSold;
        tokenId = ++_nextTokenId;

        _safeMint(msg.sender, tokenId);
        _ticketInfo[tokenId] = TicketInfo(eventId, seat);

        emit TicketMinted(tokenId, eventId, msg.sender, seat);

        if (msg.value > ev.price) {
            payable(msg.sender).transfer(msg.value - ev.price);
        }
    }

    /**
     * @notice List a ticket for resale at `price` wei.
     *         Internally approves the contract to execute the transfer on sale,
     *         following the standard ERC-721 approve/transferFrom pattern.
     */
    function listForResale(uint256 tokenId, uint256 price) external {
        require(ownerOf(tokenId) == msg.sender, "EventTicket: not the ticket owner");
        require(price > 0,                       "EventTicket: price must be > 0");
        require(resalePrice[tokenId] == 0,       "EventTicket: already listed");
        resalePrice[tokenId] = price;
        // Approve this contract to transfer the token when a buyer is found.
        _approve(address(this), tokenId, msg.sender);
        emit TicketListedForResale(tokenId, price);
    }

    /**
     * @notice Cancel an active resale listing and revoke the contract's approval.
     */
    function cancelResaleListing(uint256 tokenId) external {
        require(ownerOf(tokenId) == msg.sender, "EventTicket: not the ticket owner");
        require(resalePrice[tokenId] > 0,        "EventTicket: not listed for resale");
        resalePrice[tokenId] = 0;
        _approve(address(0), tokenId, msg.sender); // revoke approval
        emit ResaleCancelled(tokenId);
    }

    /**
     * @notice Purchase a listed resale ticket.  Seller receives ETH; buyer
     *         receives the NFT.  Follows checks-effects-interactions.
     */
    function buyResaleTicket(uint256 tokenId) external payable {
        uint256 price = resalePrice[tokenId];
        require(price > 0,            "EventTicket: not for resale");
        address seller = ownerOf(tokenId);
        require(seller != msg.sender, "EventTicket: cannot buy own ticket");
        require(msg.value >= price,   "EventTicket: insufficient payment");

        // Effects first (re-entrancy guard)
        resalePrice[tokenId] = 0;

        // Transfer NFT — _transfer is the internal auth-free function;
        // we validated all conditions above.
        _transfer(seller, msg.sender, tokenId);

        // Interactions: pay seller, refund surplus
        (bool ok, ) = payable(seller).call{value: price}("");
        require(ok, "EventTicket: payment to seller failed");
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }

        emit TicketResold(tokenId, seller, msg.sender, price);
    }

    // ─── View helpers ─────────────────────────────────────────────────────────

    /**
     * @notice Return eventId and seat number for a given ticket token.
     */
    function getTicketInfo(uint256 tokenId)
        external view
        returns (uint256 eventId, uint256 seat, address owner_)
    {
        require(_ownerOf(tokenId) != address(0), "EventTicket: token does not exist");
        TicketInfo storage ti = _ticketInfo[tokenId];
        return (ti.eventId, ti.seat, ownerOf(tokenId));
    }

    // ─── On-chain metadata ────────────────────────────────────────────────────

    /**
     * @notice ERC-721 metadata URI — returns a base64-encoded JSON object
     *         generated entirely on-chain from the stored event data.
     *
     *         Why on-chain rather than IPFS?
     *         The event details (name, date, venue, seat) are already in
     *         contract storage, so building the JSON here costs no extra
     *         storage.  On-chain metadata is permanent, censorship-resistant,
     *         and requires no external pinning service.  IPFS would be better
     *         if tickets had rich media (images, PDFs) that are too large for
     *         on-chain storage — that is not the case here.
     */
    function tokenURI(uint256 tokenId)
        public view override
        returns (string memory)
    {
        require(_ownerOf(tokenId) != address(0), "EventTicket: token does not exist");
        TicketInfo storage ti = _ticketInfo[tokenId];
        Event      storage ev = events[ti.eventId];

        string memory json = Base64.encode(bytes(string.concat(
            '{"name":"', ev.name, ' - Ticket #', tokenId.toString(), '",',
            '"description":"Event ticket for ', ev.name,
                ' on ', ev.date, ' at ', ev.venue, '",',
            '"attributes":[',
                '{"trait_type":"Event","value":"',   ev.name,  '"},',
                '{"trait_type":"Date","value":"',    ev.date,  '"},',
                '{"trait_type":"Venue","value":"',   ev.venue, '"},',
                '{"trait_type":"Seat","value":',     ti.seat.toString(), '},',
                '{"trait_type":"Event ID","value":', ti.eventId.toString(), '}',
            ']}'
        )));
        return string.concat("data:application/json;base64,", json);
    }

    // ─── Required overrides ───────────────────────────────────────────────────

    function supportsInterface(bytes4 interfaceId)
        public view override(ERC721Enumerable)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
