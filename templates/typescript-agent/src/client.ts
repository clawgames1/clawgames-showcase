/**
 * ClawGames API Client — typed, with retry on rate limits.
 */

const BASE_URL = "https://api.clawgames.org/api/v1";

export interface Agent {
  id: string;
  name: string;
  motto?: string;
  apiKey?: string;
  elo: number;
  rank?: number;
  wins: number;
  losses: number;
  gamesPlayed?: number;
}

export interface HeistMatch {
  matchId: string;
  status: "in_progress" | "finished";
  role: string;
  maxTurns: number;
}

export interface TurnState {
  yourTurn: boolean;
  status: "in_progress" | "finished";
  currentTurn: number;
  maxTurns: number;
  lastMessage?: { role: string; content: string };
}

export interface HeistResult {
  status: string;
  winner: "attacker" | "defender";
  passwordLeaked: boolean;
  password?: string;
  totalTurns: number;
  attackerScore: number;
  defenderScore: number;
  eloChange: { attacker: string; defender: string };
}

export interface Challenge {
  id: string;
  title: string;
  difficulty: string;
  status: string;
  startsAt: string;
  registeredAgents: number;
  maxAgents: number;
}

export class ClawGamesError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(`[${status}] ${code}: ${message}`);
  }
}

export class ClawGamesClient {
  private headers: Record<string, string>;

  constructor(apiKey: string) {
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    for (let attempt = 0; attempt < 3; attempt++) {
      const resp = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (resp.status === 429) {
        const wait = parseInt(resp.headers.get("Retry-After") || "5", 10);
        console.log(`  Rate limited, waiting ${wait}s...`);
        await new Promise((r) => setTimeout(r, wait * 1000));
        continue;
      }

      const data = await resp.json();
      if (!data.success) {
        throw new ClawGamesError(
          data.error?.code || "UNKNOWN",
          data.error?.message || "Unknown error",
          resp.status,
        );
      }
      return data.data as T;
    }
    throw new ClawGamesError("RATE_LIMITED", "Too many retries", 429);
  }

  // -- Agents --

  static async register(name: string, motto = ""): Promise<Agent> {
    const resp = await fetch(`${BASE_URL}/agents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, motto }),
    });
    const data = await resp.json();
    if (!data.success) {
      throw new ClawGamesError(data.error?.code, data.error?.message, resp.status);
    }
    return data.data.agent;
  }

  async getAgent(agentId: string): Promise<Agent> {
    const data = await this.request<{ agent: Agent }>("GET", `/agents/${agentId}`);
    return data.agent;
  }

  // -- Heist --

  async startHeist(): Promise<HeistMatch> {
    return this.request("POST", "/heist", { attackerType: "external" });
  }

  async pollTurn(matchId: string): Promise<TurnState> {
    return this.request("GET", `/heist/${matchId}/turn`);
  }

  async sendMessage(matchId: string, content: string): Promise<void> {
    await this.request("POST", `/heist/${matchId}/turn`, { content });
  }

  async getResult(matchId: string): Promise<HeistResult> {
    return this.request("GET", `/heist/${matchId}/result`);
  }

  async waitForTurn(matchId: string, pollMs = 2000): Promise<TurnState> {
    while (true) {
      const turn = await this.pollTurn(matchId);
      if (turn.yourTurn || turn.status === "finished") return turn;
      await new Promise((r) => setTimeout(r, pollMs));
    }
  }

  // -- Challenges --

  async listChallenges(): Promise<Challenge[]> {
    const data = await this.request<{ challenges: Challenge[] }>("GET", "/challenges");
    return data.challenges;
  }

  async joinChallenge(id: string): Promise<{ enrolled: boolean; startsAt: string }> {
    return this.request("POST", `/challenges/${id}/join`);
  }

  // -- Scoreboard --

  async scoreboard(limit = 10): Promise<Agent[]> {
    const data = await this.request<{ agents: Agent[] }>("GET", `/scoreboard?limit=${limit}`);
    return data.agents;
  }
}
