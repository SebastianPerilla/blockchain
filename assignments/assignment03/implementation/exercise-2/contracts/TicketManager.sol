// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title TicketManager — on-chain event ticketing with purchase, transfer, and resale
contract TicketManager {
    address public admin;

    struct Event {
        uint256 id;
        string  name;
        string  date;
        string  venue;
        uint256 price;         // in wei
        uint256 totalTickets;
        uint256 ticketsSold;
        bool    active;
    }

    struct Ticket {
        uint256 id;
        uint256 eventId;
        address owner;
        bool    forResale;
        uint256 resalePrice;   // in wei
    }

    uint256 public nextEventId  = 1;
    uint256 public nextTicketId = 1;

    mapping(uint256 => Event)    public events;
    mapping(uint256 => Ticket)   public tickets;
    mapping(address => uint256[]) private _userTickets;

    // ── Events (log) ────────────────────────────────────────────────────────
    event EventCreated(uint256 indexed eventId, string name, uint256 price, uint256 totalTickets);
    event TicketPurchased(uint256 indexed ticketId, uint256 indexed eventId, address indexed buyer);
    event TicketTransferred(uint256 indexed ticketId, address indexed from, address indexed to);
    event TicketListedForResale(uint256 indexed ticketId, uint256 resalePrice);
    event TicketResold(uint256 indexed ticketId, address indexed from, address indexed to, uint256 price);
    event ResaleCancelled(uint256 indexed ticketId);
    event EventDeactivated(uint256 indexed eventId);

    // ── Modifiers ────────────────────────────────────────────────────────────
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this");
        _;
    }

    modifier onlyOwner(uint256 ticketId) {
        require(tickets[ticketId].owner == msg.sender, "Not the ticket owner");
        _;
    }

    // ── Constructor ──────────────────────────────────────────────────────────
    constructor() {
        admin = msg.sender;
    }

    // ── Admin functions ──────────────────────────────────────────────────────

    /// @notice Create a new ticketed event (admin only)
    function createEvent(
        string memory name,
        string memory date,
        string memory venue,
        uint256 price,
        uint256 totalTickets
    ) external onlyAdmin returns (uint256 eventId) {
        require(totalTickets > 0, "Must have at least one ticket");
        eventId = nextEventId++;
        events[eventId] = Event({
            id:           eventId,
            name:         name,
            date:         date,
            venue:        venue,
            price:        price,
            totalTickets: totalTickets,
            ticketsSold:  0,
            active:       true
        });
        emit EventCreated(eventId, name, price, totalTickets);
    }

    /// @notice Deactivate an event so no more tickets can be sold (admin only)
    function deactivateEvent(uint256 eventId) external onlyAdmin {
        require(events[eventId].active, "Event already inactive");
        events[eventId].active = false;
        emit EventDeactivated(eventId);
    }

    // ── User functions ───────────────────────────────────────────────────────

    /// @notice Buy a primary-sale ticket for an event
    function buyTicket(uint256 eventId) external payable returns (uint256 ticketId) {
        Event storage evt = events[eventId];
        require(evt.id != 0,                     "Event does not exist");
        require(evt.active,                       "Event is not active");
        require(evt.ticketsSold < evt.totalTickets, "Sold out");
        require(msg.value >= evt.price,           "Insufficient payment");

        ticketId = nextTicketId++;
        tickets[ticketId] = Ticket({
            id:          ticketId,
            eventId:     eventId,
            owner:       msg.sender,
            forResale:   false,
            resalePrice: 0
        });
        _userTickets[msg.sender].push(ticketId);
        evt.ticketsSold++;

        // Refund any excess payment
        if (msg.value > evt.price) {
            payable(msg.sender).transfer(msg.value - evt.price);
        }
        emit TicketPurchased(ticketId, eventId, msg.sender);
    }

    /// @notice Transfer a ticket to another address (not allowed while listed for resale)
    function transferTicket(uint256 ticketId, address to) external onlyOwner(ticketId) {
        require(to != address(0),              "Invalid recipient");
        require(to != msg.sender,              "Cannot transfer to yourself");
        require(!tickets[ticketId].forResale,  "Cancel resale listing first");

        address from = msg.sender;
        tickets[ticketId].owner = to;
        _removeFromUser(from, ticketId);
        _userTickets[to].push(ticketId);
        emit TicketTransferred(ticketId, from, to);
    }

    /// @notice List a ticket for resale at a given price
    function listForResale(uint256 ticketId, uint256 price) external onlyOwner(ticketId) {
        require(price > 0,                     "Resale price must be > 0");
        require(!tickets[ticketId].forResale,  "Already listed for resale");
        tickets[ticketId].forResale   = true;
        tickets[ticketId].resalePrice = price;
        emit TicketListedForResale(ticketId, price);
    }

    /// @notice Cancel a resale listing (owner reclaims the ticket)
    function cancelResaleListing(uint256 ticketId) external onlyOwner(ticketId) {
        require(tickets[ticketId].forResale, "Not listed for resale");
        tickets[ticketId].forResale   = false;
        tickets[ticketId].resalePrice = 0;
        emit ResaleCancelled(ticketId);
    }

    /// @notice Buy a ticket that has been listed for resale
    function buyResaleTicket(uint256 ticketId) external payable {
        Ticket storage tkt = tickets[ticketId];
        require(tkt.forResale,                 "Ticket not for resale");
        require(tkt.owner != msg.sender,       "Cannot buy your own ticket");
        require(msg.value >= tkt.resalePrice,  "Insufficient payment");

        address seller = tkt.owner;
        uint256 price  = tkt.resalePrice;

        // Effects before interactions (reentrancy safe)
        tkt.owner       = msg.sender;
        tkt.forResale   = false;
        tkt.resalePrice = 0;

        _removeFromUser(seller, ticketId);
        _userTickets[msg.sender].push(ticketId);

        payable(seller).transfer(price);
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }
        emit TicketResold(ticketId, seller, msg.sender, price);
    }

    // ── View helpers ─────────────────────────────────────────────────────────

    function getUserTickets(address user) external view returns (uint256[] memory) {
        return _userTickets[user];
    }

    function getTicket(uint256 ticketId)
        external
        view
        returns (
            uint256 id,
            uint256 eventId,
            address owner,
            bool    forResale,
            uint256 resalePrice
        )
    {
        Ticket storage t = tickets[ticketId];
        return (t.id, t.eventId, t.owner, t.forResale, t.resalePrice);
    }

    // ── Internal helpers ─────────────────────────────────────────────────────

    function _removeFromUser(address user, uint256 ticketId) internal {
        uint256[] storage arr = _userTickets[user];
        for (uint256 i = 0; i < arr.length; i++) {
            if (arr[i] == ticketId) {
                arr[i] = arr[arr.length - 1];
                arr.pop();
                break;
            }
        }
    }
}
