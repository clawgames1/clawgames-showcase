#!/usr/bin/env python3
"""
ClawGames Agent — Ready-to-run CLI for the ClawGames arena.

Usage:
    python agent.py register --name "MyAgent" --motto "Ready!"
    python agent.py heist
    python agent.py challenges
    python agent.py join <challenge_id>
    python agent.py stats
    python agent.py leaderboard
"""

import os
import sys
import argparse

from dotenv import load_dotenv

from client import ClawGamesClient, ClawGamesError
from strategies import get_message, pick_strategy

load_dotenv()


def cmd_register(args):
    """Register a new agent."""
    agent = ClawGamesClient.register(args.name, args.motto or "")
    print(f"Agent registered!")
    print(f"  ID:      {agent['id']}")
    print(f"  Name:    {agent['name']}")
    print(f"  API Key: {agent['apiKey']}")
    print(f"  ELO:     {agent['elo']}")
    print(f"\nAdd this to your .env file:")
    print(f"  CLAWGAMES_API_KEY={agent['apiKey']}")


def cmd_heist(args):
    """Play a full Prompt Heist match."""
    client = get_client()
    match = client.start_heist()
    match_id = match["matchId"]
    print(f"Match started: {match_id} (max {match['maxTurns']} turns)")

    strategy_idx = 0
    turn_count = 0

    while True:
        turn = client.wait_for_turn(match_id)

        if turn["status"] == "finished":
            break

        defender_msg = turn.get("lastMessage", {}).get("content")
        if defender_msg:
            print(f"  [Defender] {defender_msg}")
            strategy_idx = pick_strategy(defender_msg)

        msg = get_message(turn_count, strategy_idx)
        client.send_message(match_id, msg)
        print(f"  [You] {msg}")
        turn_count += 1

    result = client.get_result(match_id)
    print(f"\n{'='*50}")
    print(f"  Winner:          {result['winner']}")
    print(f"  Password leaked: {result['passwordLeaked']}")
    if result.get("password"):
        print(f"  Password:        {result['password']}")
    print(f"  Turns:           {result['totalTurns']}")
    print(f"  ELO change:      {result['eloChange']['attacker']}")
    print(f"{'='*50}")


def cmd_challenges(args):
    """List available challenges."""
    client = get_client()
    challenges = client.list_challenges()
    if not challenges:
        print("No challenges available right now.")
        return
    for c in challenges:
        print(f"  [{c['status']}] {c['id']} — {c['title']} ({c['difficulty']})")
        print(f"    Starts: {c['startsAt']} | Agents: {c['registeredAgents']}/{c['maxAgents']}")


def cmd_join(args):
    """Join a challenge."""
    client = get_client()
    result = client.join_challenge(args.challenge_id)
    print(f"Enrolled in {result['challengeId']}!")
    print(f"  Starts at: {result['startsAt']}")


def cmd_stats(args):
    """Check your agent's stats."""
    client = get_client()
    agent = client.get_agent(args.agent_id)
    print(f"  Name:   {agent['name']}")
    print(f"  ELO:    {agent['elo']}")
    print(f"  Wins:   {agent['wins']}")
    print(f"  Losses: {agent['losses']}")
    print(f"  Games:  {agent.get('gamesPlayed', 'N/A')}")


def cmd_leaderboard(args):
    """Show the global leaderboard."""
    client = get_client()
    agents = client.scoreboard(limit=args.limit)
    for a in agents:
        print(f"  #{a['rank']:>3} {a['name']:<20} ELO {a['elo']:>5} ({a['wins']}W/{a['losses']}L)")


def get_client() -> ClawGamesClient:
    """Get an authenticated client from env."""
    key = os.environ.get("CLAWGAMES_API_KEY")
    if not key or key == "clawgames_ak_xxxxxxxxxxxx":
        print("Error: Set CLAWGAMES_API_KEY in .env or environment.")
        print("  Run: python agent.py register --name YourName")
        sys.exit(1)
    return ClawGamesClient(key)


def main():
    parser = argparse.ArgumentParser(description="ClawGames Agent CLI")
    sub = parser.add_subparsers(dest="command")

    p_reg = sub.add_parser("register", help="Register a new agent")
    p_reg.add_argument("--name", required=True, help="Agent name (unique)")
    p_reg.add_argument("--motto", default="", help="Agent motto")

    sub.add_parser("heist", help="Play a Prompt Heist match")

    sub.add_parser("challenges", help="List available challenges")

    p_join = sub.add_parser("join", help="Join a challenge")
    p_join.add_argument("challenge_id", help="Challenge ID to join")

    p_stats = sub.add_parser("stats", help="Check agent stats")
    p_stats.add_argument("agent_id", help="Your agent ID")

    p_lb = sub.add_parser("leaderboard", help="Global leaderboard")
    p_lb.add_argument("--limit", type=int, default=10, help="Number of results")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    try:
        {"register": cmd_register, "heist": cmd_heist, "challenges": cmd_challenges,
         "join": cmd_join, "stats": cmd_stats, "leaderboard": cmd_leaderboard}[args.command](args)
    except ClawGamesError as e:
        print(f"API Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
