"""
Exercise 2 — Part A: Web2 Event Ticket Booking System
Backend: SQLite   |   Frontend: Streamlit
"""
import os
import sqlite3

import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web2_tickets.db")


# ── Database initialisation ────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            date          TEXT    NOT NULL,
            venue         TEXT    NOT NULL,
            price         REAL    NOT NULL,
            total_tickets INTEGER NOT NULL,
            tickets_sold  INTEGER NOT NULL DEFAULT 0,
            active        INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    INTEGER NOT NULL,
            owner_id    INTEGER NOT NULL,
            for_resale  INTEGER NOT NULL DEFAULT 0,
            resale_price REAL   NOT NULL DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );
    """)

    # Seed users
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO users (username, role) VALUES (?, ?)",
            [("admin", "admin"), ("alice", "user"), ("bob", "user")],
        )

    # Seed events
    if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO events (name, date, venue, price, total_tickets) VALUES (?, ?, ?, ?, ?)",
            [
                ("Summer Music Festival", "2025-06-15", "Central Park, NYC",         50.0,  100),
                ("Tech Conference 2025",  "2025-09-20", "Convention Centre, SF",    150.0,   50),
            ],
        )
    conn.commit()
    conn.close()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def get_users():
    with _get_db() as c:
        return c.execute("SELECT * FROM users").fetchall()


def get_events(active_only: bool = True):
    with _get_db() as c:
        if active_only:
            return c.execute("SELECT * FROM events WHERE active = 1 ORDER BY id").fetchall()
        return c.execute("SELECT * FROM events ORDER BY id").fetchall()


def get_user_tickets(user_id: int):
    with _get_db() as c:
        return c.execute(
            """
            SELECT t.*, e.name AS event_name, e.date AS event_date, e.venue
            FROM   tickets t
            JOIN   events  e ON t.event_id = e.id
            WHERE  t.owner_id = ?
            ORDER BY t.id
            """,
            (user_id,),
        ).fetchall()


def get_resale_tickets():
    with _get_db() as c:
        return c.execute(
            """
            SELECT t.*, e.name AS event_name, e.date AS event_date,
                   e.venue, u.username AS seller_name
            FROM   tickets t
            JOIN   events  e ON t.event_id = e.id
            JOIN   users   u ON t.owner_id = u.id
            WHERE  t.for_resale = 1
            ORDER BY t.id
            """,
        ).fetchall()


def get_all_tickets():
    with _get_db() as c:
        return c.execute(
            """
            SELECT t.*, e.name AS event_name, u.username AS owner_name
            FROM   tickets t
            JOIN   events  e ON t.event_id = e.id
            JOIN   users   u ON t.owner_id = u.id
            ORDER BY t.id
            """,
        ).fetchall()


# ── Business logic ─────────────────────────────────────────────────────────────

def buy_ticket(user_id: int, event_id: int):
    conn = _get_db()
    try:
        event = conn.execute(
            "SELECT * FROM events WHERE id = ? AND active = 1", (event_id,)
        ).fetchone()
        if not event:
            return False, "Event not found or inactive."
        if event["tickets_sold"] >= event["total_tickets"]:
            return False, "Sorry, this event is sold out."
        conn.execute(
            "INSERT INTO tickets (event_id, owner_id) VALUES (?, ?)", (event_id, user_id)
        )
        conn.execute(
            "UPDATE events SET tickets_sold = tickets_sold + 1 WHERE id = ?", (event_id,)
        )
        conn.commit()
        return True, "Ticket purchased!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def transfer_ticket(ticket_id: int, from_user_id: int, to_username: str):
    conn = _get_db()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ? AND owner_id = ?", (ticket_id, from_user_id)
        ).fetchone()
        if not ticket:
            return False, "Ticket not found or you don't own it."
        if ticket["for_resale"]:
            return False, "Cancel the resale listing before transferring."
        to_user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (to_username,)
        ).fetchone()
        if not to_user:
            return False, "Recipient user not found."
        if to_user["id"] == from_user_id:
            return False, "Cannot transfer to yourself."
        conn.execute(
            "UPDATE tickets SET owner_id = ? WHERE id = ?", (to_user["id"], ticket_id)
        )
        conn.commit()
        return True, f"Ticket #{ticket_id} transferred to {to_username}!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def list_for_resale(ticket_id: int, user_id: int, price: float):
    conn = _get_db()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ? AND owner_id = ?", (ticket_id, user_id)
        ).fetchone()
        if not ticket:
            return False, "Ticket not found or you don't own it."
        if ticket["for_resale"]:
            return False, "Already listed for resale."
        if price <= 0:
            return False, "Price must be positive."
        conn.execute(
            "UPDATE tickets SET for_resale = 1, resale_price = ? WHERE id = ?",
            (price, ticket_id),
        )
        conn.commit()
        return True, f"Ticket #{ticket_id} listed for resale at ${price:.2f}!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def cancel_resale(ticket_id: int, user_id: int):
    conn = _get_db()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ? AND owner_id = ? AND for_resale = 1",
            (ticket_id, user_id),
        ).fetchone()
        if not ticket:
            return False, "No active resale listing found for this ticket."
        conn.execute(
            "UPDATE tickets SET for_resale = 0, resale_price = 0 WHERE id = ?", (ticket_id,)
        )
        conn.commit()
        return True, "Resale listing cancelled."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def buy_resale_ticket(ticket_id: int, buyer_id: int):
    conn = _get_db()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ? AND for_resale = 1", (ticket_id,)
        ).fetchone()
        if not ticket:
            return False, "Ticket not available for resale."
        if ticket["owner_id"] == buyer_id:
            return False, "Cannot buy your own ticket."
        conn.execute(
            "UPDATE tickets SET owner_id = ?, for_resale = 0, resale_price = 0 WHERE id = ?",
            (buyer_id, ticket_id),
        )
        conn.commit()
        return True, f"Resale ticket #{ticket_id} purchased!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def create_event(name: str, date: str, venue: str, price: float, total_tickets: int):
    conn = _get_db()
    try:
        conn.execute(
            "INSERT INTO events (name, date, venue, price, total_tickets) VALUES (?, ?, ?, ?, ?)",
            (name, date, venue, price, total_tickets),
        )
        conn.commit()
        return True, f"Event '{name}' created!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def deactivate_event(event_id: int):
    conn = _get_db()
    try:
        conn.execute("UPDATE events SET active = 0 WHERE id = ?", (event_id,))
        conn.commit()
        return True, "Event deactivated."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _badge(text: str, colour: str) -> str:
    return (
        f'<span style="background:{colour};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.78em;">{text}</span>'
    )


# ── Main app ───────────────────────────────────────────────────────────────────

def main() -> None:
    init_db()

    st.set_page_config(page_title="TicketChain Web2", page_icon="🎫", layout="wide")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🎫 TicketChain")
        st.markdown(_badge("WEB2 — SQLite", "#1a56db"), unsafe_allow_html=True)
        st.divider()

        users = get_users()
        username_map = {u["username"]: dict(u) for u in users}
        selected = st.selectbox("Select user", list(username_map.keys()))
        current  = username_map[selected]
        is_admin = current["role"] == "admin"

        if is_admin:
            st.success("Logged in as **Admin**")
        else:
            st.info(f"Logged in as **{current['username']}**")

        st.divider()
        st.caption("No blockchain — all data stored in a local SQLite database.")

    # ── Page header ──────────────────────────────────────────────────────────
    st.title("🎫 Event Ticket Booking")
    st.caption("Web2 version — persistent storage via SQLite")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    if is_admin:
        t_events, t_resale, t_all, t_admin = st.tabs(
            ["Browse Events", "Resale Market", "All Tickets", "Admin Panel"]
        )
    else:
        t_events, t_mine, t_resale = st.tabs(
            ["Browse Events", "My Tickets", "Resale Market"]
        )

    # ── Browse Events ─────────────────────────────────────────────────────────
    with t_events:
        st.header("Available Events")
        events = get_events(active_only=True)
        if not events:
            st.info("No active events right now.")
        for ev in events:
            avail = ev["total_tickets"] - ev["tickets_sold"]
            with st.expander(f"**{ev['name']}** — {ev['date']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Venue:** {ev['venue']}")
                    st.write(f"**Date:** {ev['date']}")
                    st.write(f"**Price:** ${ev['price']:.2f}")
                with c2:
                    st.write(f"**Available:** {avail} / {ev['total_tickets']}")
                    if ev["total_tickets"] > 0:
                        st.progress(ev["tickets_sold"] / ev["total_tickets"])

                if not is_admin:
                    if avail > 0:
                        if st.button(
                            f"Buy ticket — ${ev['price']:.2f}",
                            key=f"buy_{ev['id']}",
                        ):
                            ok, msg = buy_ticket(current["id"], ev["id"])
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()
                    else:
                        st.warning("Sold out")

    # ── My Tickets (user only) ────────────────────────────────────────────────
    if not is_admin:
        with t_mine:
            st.header("My Tickets")
            my_tickets = get_user_tickets(current["id"])
            if not my_tickets:
                st.info("You don't own any tickets yet.")

            for tk in my_tickets:
                label = (
                    f"Ticket #{tk['id']} — {tk['event_name']}  "
                    + ("🔴 For Resale" if tk["for_resale"] else "✅ Active")
                )
                with st.expander(label):
                    st.write(f"**Event:** {tk['event_name']}  |  **Date:** {tk['event_date']}  |  **Venue:** {tk['venue']}")

                    if tk["for_resale"]:
                        st.write(f"**Listed at:** ${tk['resale_price']:.2f}")
                        if st.button("Cancel resale listing", key=f"cancel_{tk['id']}"):
                            ok, msg = cancel_resale(tk["id"], current["id"])
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()
                    else:
                        col_t, col_r = st.columns(2)

                        with col_t:
                            st.subheader("Transfer")
                            other_users = [
                                u["username"]
                                for u in users
                                if u["username"] != current["username"] and u["role"] == "user"
                            ]
                            if other_users:
                                to = st.selectbox("To user", other_users, key=f"to_{tk['id']}")
                                if st.button("Transfer", key=f"tr_{tk['id']}"):
                                    ok, msg = transfer_ticket(tk["id"], current["id"], to)
                                    (st.success if ok else st.error)(msg)
                                    if ok:
                                        st.rerun()
                            else:
                                st.caption("No other users available.")

                        with col_r:
                            st.subheader("Resale")
                            price = st.number_input(
                                "Price ($)", min_value=0.01, value=75.0,
                                step=5.0, key=f"rp_{tk['id']}"
                            )
                            if st.button("List for resale", key=f"lr_{tk['id']}"):
                                ok, msg = list_for_resale(tk["id"], current["id"], price)
                                (st.success if ok else st.error)(msg)
                                if ok:
                                    st.rerun()

    # ── Resale Market ─────────────────────────────────────────────────────────
    with t_resale:
        st.header("Resale Market")
        resale = get_resale_tickets()
        if not resale:
            st.info("No tickets listed for resale.")
        for tk in resale:
            with st.expander(f"Ticket #{tk['id']} — {tk['event_name']} — ${tk['resale_price']:.2f}"):
                st.write(
                    f"**Event:** {tk['event_name']}  |  "
                    f"**Date:** {tk['event_date']}  |  "
                    f"**Venue:** {tk['venue']}"
                )
                st.write(f"**Seller:** {tk['seller_name']}  |  **Price:** ${tk['resale_price']:.2f}")
                if not is_admin and tk["owner_id"] != current["id"]:
                    if st.button(f"Buy for ${tk['resale_price']:.2f}", key=f"br_{tk['id']}"):
                        ok, msg = buy_resale_ticket(tk["id"], current["id"])
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()

    # ── Admin Panel ───────────────────────────────────────────────────────────
    if is_admin:
        with t_admin:
            st.header("Admin Panel")

            st.subheader("Create New Event")
            with st.form("create_event"):
                name   = st.text_input("Event name")
                date   = st.date_input("Date")
                venue  = st.text_input("Venue")
                price  = st.number_input("Ticket price ($)", min_value=0.01, value=50.0, step=5.0)
                total  = st.number_input("Total tickets",    min_value=1,    value=100,  step=10)
                if st.form_submit_button("Create event"):
                    if name and venue:
                        ok, msg = create_event(name, str(date), venue, price, int(total))
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
                    else:
                        st.warning("Name and venue are required.")

            st.divider()
            st.subheader("Manage Events")
            for ev in get_events(active_only=False):
                status = "Active" if ev["active"] else "Inactive"
                with st.expander(f"{ev['name']} — {status}"):
                    st.write(
                        f"**Venue:** {ev['venue']}  |  "
                        f"**Date:** {ev['date']}  |  "
                        f"**Price:** ${ev['price']:.2f}  |  "
                        f"**Sold:** {ev['tickets_sold']} / {ev['total_tickets']}"
                    )
                    if ev["active"]:
                        if st.button("Deactivate", key=f"deact_{ev['id']}"):
                            ok, msg = deactivate_event(ev["id"])
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()

        with t_all:
            st.header("All Tickets")
            all_t = get_all_tickets()
            if not all_t:
                st.info("No tickets sold yet.")
            else:
                rows = []
                for t in all_t:
                    rows.append({
                        "Ticket ID":   t["id"],
                        "Event":       t["event_name"],
                        "Owner":       t["owner_name"],
                        "For Resale":  bool(t["for_resale"]),
                        "Resale Price": f"${t['resale_price']:.2f}" if t["for_resale"] else "—",
                    })
                st.dataframe(rows, use_container_width=True)


if __name__ == "__main__":
    main()
