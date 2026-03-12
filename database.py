import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "gg_bot.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Ranking tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ranking_users (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            PRIMARY KEY (guild_id, user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ranking_roles (
            guild_id TEXT NOT NULL,
            xp_req INTEGER NOT NULL,
            role_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, xp_req)
        )
    ''')

    # Roles tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles_auto (
            guild_id TEXT PRIMARY KEY,
            role_id TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles_menus (
            guild_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, message_id)
        )
    ''')

    # Status meta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_meta (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL
        )
    ''')

    # VC leaderboard meta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vc_lb_meta (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL
        )
    ''')

    # VC points
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vc_points (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    ''')

    conn.commit()
    conn.close()

# Ranking functions
def load_ranking_data():
    conn = get_connection()
    cursor = conn.cursor()

    users = {}
    cursor.execute('SELECT guild_id, user_id, xp, active FROM ranking_users')
    for row in cursor.fetchall():
        guild_id, user_id, xp, active = row
        if guild_id not in users:
            users[guild_id] = {}
        users[guild_id][user_id] = {"xp": xp, "active": bool(active)}

    rank_roles = {}
    cursor.execute('SELECT guild_id, xp_req, role_id FROM ranking_roles')
    for row in cursor.fetchall():
        guild_id, xp_req, role_id = row
        # SQLite returns TEXT for the role_id column; convert to int for discord
        try:
            role_id = int(role_id)
        except Exception:
            pass
        if guild_id not in rank_roles:
            rank_roles[guild_id] = {}
        rank_roles[guild_id][str(xp_req)] = role_id

    conn.close()
    return {"users": users, "rank_roles": rank_roles}

def save_ranking_data(data):
    conn = get_connection()
    cursor = conn.cursor()

    # Clear tables
    cursor.execute('DELETE FROM ranking_users')
    cursor.execute('DELETE FROM ranking_roles')

    # Insert users
    for guild_id, users in data["users"].items():
        for user_id, user_data in users.items():
            cursor.execute('INSERT INTO ranking_users (guild_id, user_id, xp, active) VALUES (?, ?, ?, ?)',
                           (guild_id, user_id, user_data["xp"], user_data["active"]))

    # Insert roles
    for guild_id, roles in data["rank_roles"].items():
        for xp_req, role_id in roles.items():
            cursor.execute('INSERT INTO ranking_roles (guild_id, xp_req, role_id) VALUES (?, ?, ?)',
                           (guild_id, int(xp_req), role_id))

    conn.commit()
    conn.close()

# Roles functions
def load_roles_data():
    conn = get_connection()
    cursor = conn.cursor()

    data = {}
    cursor.execute('SELECT guild_id, role_id FROM roles_auto')
    for row in cursor.fetchall():
        guild_id, role_id = row
        try:
            role_id = int(role_id)
        except Exception:
            pass
        if guild_id not in data:
            data[guild_id] = {"messages": {}, "auto_role": role_id}

    cursor.execute('SELECT guild_id, message_id, channel_id FROM roles_menus')
    for row in cursor.fetchall():
        guild_id, message_id, channel_id = row
        try:
            message_id = int(message_id)
        except Exception:
            pass
        try:
            channel_id = int(channel_id)
        except Exception:
            pass
        if guild_id not in data:
            data[guild_id] = {"messages": {}, "auto_role": None}
        # store message_id as string key for consistency with how other code uses it
        data[guild_id]["messages"][str(message_id)] = {"channel_id": channel_id, "mappings": {}}

    conn.close()
    return data

def save_roles_data(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM roles_auto')
    cursor.execute('DELETE FROM roles_menus')

    for guild_id, guild_data in data.items():
        if "auto_role" in guild_data and guild_data["auto_role"]:
            cursor.execute('INSERT INTO roles_auto (guild_id, role_id) VALUES (?, ?)',
                           (guild_id, guild_data["auto_role"]))

        for message_id, msg_data in guild_data.get("messages", {}).items():
            cursor.execute('INSERT INTO roles_menus (guild_id, message_id, channel_id) VALUES (?, ?, ?)',
                           (guild_id, message_id, msg_data["channel_id"]))

    conn.commit()
    conn.close()

# Status meta functions
def load_status_meta():
    conn = get_connection()
    cursor = conn.cursor()

    data = {}
    cursor.execute('SELECT guild_id, channel_id, message_id FROM status_meta')
    for row in cursor.fetchall():
        guild_id, channel_id, message_id = row
        # convert to ints so get_channel/fetch_message accept them
        try:
            channel_id = int(channel_id)
        except Exception:
            pass
        try:
            message_id = int(message_id)
        except Exception:
            pass
        data[guild_id] = {"channel_id": channel_id, "message_id": message_id}

    conn.close()
    return data

def save_status_meta(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM status_meta')

    for guild_id, meta in data.items():
        cursor.execute('INSERT INTO status_meta (guild_id, channel_id, message_id) VALUES (?, ?, ?)',
                       (guild_id, meta["channel_id"], meta["message_id"]))

    conn.commit()
    conn.close()

# VC LB meta functions
def load_vc_lb_meta():
    conn = get_connection()
    cursor = conn.cursor()

    data = {}
    cursor.execute('SELECT guild_id, channel_id, message_id FROM vc_lb_meta')
    for row in cursor.fetchall():
        guild_id, channel_id, message_id = row
        try:
            channel_id = int(channel_id)
        except Exception:
            pass
        try:
            message_id = int(message_id)
        except Exception:
            pass
        data[guild_id] = {"channel_id": channel_id, "message_id": message_id}

    conn.close()
    return data

def save_vc_lb_meta(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM vc_lb_meta')

    for guild_id, meta in data.items():
        cursor.execute('INSERT INTO vc_lb_meta (guild_id, channel_id, message_id) VALUES (?, ?, ?)',
                       (guild_id, meta["channel_id"], meta["message_id"]))

    conn.commit()
    conn.close()

# VC points functions
def load_vc_points():
    conn = get_connection()
    cursor = conn.cursor()

    data = {}
    cursor.execute('SELECT guild_id, user_id, points FROM vc_points')
    for row in cursor.fetchall():
        guild_id, user_id, points = row
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id][user_id] = points

    conn.close()
    return data

def save_vc_points(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM vc_points')

    for guild_id, users in data.items():
        for user_id, points in users.items():
            cursor.execute('INSERT INTO vc_points (guild_id, user_id, points) VALUES (?, ?, ?)',
                           (guild_id, user_id, points))

    conn.commit()
    conn.close()

# Initialize DB on import
init_db()