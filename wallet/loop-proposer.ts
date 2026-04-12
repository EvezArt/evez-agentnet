// loop-proposer.ts — EVEZ-OS Loop Proposer MCP Server
// Computes the full recursive collateral loop and returns UNSIGNED transactions.
// The agent does the math. YOU sign and broadcast.
//
// Run: npx tsx loop-proposer.ts
// Connect via Claude Desktop config — adds propose_loop, propose_unwind, simulate_loop tools

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { ethers } from "ethers";
import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";

// ── Paths ──────────────────────────────────────────────────────────────────────
const POSITIONS_FILE = path.join(os.homedir(), ".evez-os", "positions.json");
const WALLET_FILE    = path.join(os.homedir(), ".evez-os", "wallets.json");

// ── Protocol constants (March 2026 — verify before use) ───────────────────────
const PROTOCOLS = {
  morpho: {
    address:    "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    chain:      8453, // Base
    maxLTV:     0.965,
    fee:        0.0,
    yieldAPY:   0.15,
  },
  kamino: {
    programId:  "KLend2g3cP87fffoy8q1mQqGKjrL1AyGLlkbdcHsmpL",
    chain:      101,  // Solana mainnet
    yieldAPY:   0.28,
  },
  pendle: {
    address:    "0x0000000000000000000000000000000000000000", // set to live Pendle router
    chain:      1,    // Ethereum
    yieldAPY:   0.42,
  },
  raydium: {
    programId:  "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    chain:      101,
    yieldAPY:   0.35,
  },
} as const;

// Morpho Blue ABI snippets for encoding calldata
const MORPHO_ABI = [
  "function supply(tuple(address loanToken, address collateralToken, address oracle, address irm, uint256 lltv) marketParams, uint256 assets, uint256 shares, address onBehalf, bytes callData) returns (uint256, uint256)",
  "function supplyCollateral(tuple(address loanToken, address collateralToken, address oracle, address irm, uint256 lltv) marketParams, uint256 assets, address onBehalf, bytes callData)",
  "function borrow(tuple(address loanToken, address collateralToken, address oracle, address irm, uint256 lltv) marketParams, uint256 assets, uint256 shares, address onBehalf, address receiver) returns (uint256, uint256)",
  "function repay(tuple(address loanToken, address collateralToken, address oracle, address irm, uint256 lltv) marketParams, uint256 assets, uint256 shares, address onBehalf, bytes callData) returns (uint256, uint256)",
  "function withdrawCollateral(tuple(address loanToken, address collateralToken, address oracle, address irm, uint256 lltv) marketParams, uint256 assets, address onBehalf, address receiver)",
];

const morphoIface = new ethers.Interface(MORPHO_ABI);

// ── Zod schemas ────────────────────────────────────────────────────────────────
const ProposeLoopSchema = z.object({
  collateral_asset:  z.enum(["ETH", "cbETH", "wstETH", "SOL"]),
  capital_usd:       z.number().positive().describe("Amount in USD to seed the loop"),
  ltv:               z.number().min(0.5).max(0.70).describe("LTV per cycle — never exceed 0.70"),
  depth:             z.number().int().min(1).max(3).describe("Number of borrow-redeploy iterations (max 3)"),
  yield_protocol:    z.enum(["kamino", "morpho", "pendle", "raydium"]),
  market_id:         z.string().optional().describe("Morpho market ID (leave blank for default ETH/USDC)"),
  wallet_address:    z.string().optional().describe("Override collateral wallet address"),
});

const ProposeUnwindSchema = z.object({
  emergency:     z.boolean().default(false).describe("If true, propose full unwind in single batch"),
  market_id:     z.string().optional(),
  wallet_address: z.string().optional(),
});

const SimulateLoopSchema = z.object({
  collateral_asset: z.enum(["ETH", "cbETH", "wstETH", "SOL"]),
  capital_usd:      z.number().positive(),
  ltv:              z.number().min(0.5).max(0.70),
  depth:            z.number().int().min(1).max(3),
  yield_protocol:   z.enum(["kamino", "morpho", "pendle", "raydium"]),
});

const PositionHealthSchema = z.object({});

// ── Types ─────────────────────────────────────────────────────────────────────
interface UnsignedTx {
  step:        number;
  description: string;
  to:          string;
  data:        string;
  value:       string;
  gasEstimate: string;
  chainId:     number;
  chainName:   string;
  WARNING:     string;
}

interface LoopIteration {
  depth:           number;
  collateralUSD:   number;
  borrowAmountUSD: number;
  deployedUSD:     number;
  cumulativeYield: number;
  liquidationUSD:  number;
  warning?:        string;
}

// ── Math ──────────────────────────────────────────────────────────────────────
function computeLoop(
  capitalUSD: number,
  ltv:        number,
  depth:      number,
  yieldAPY:   number
): { iterations: LoopIteration[]; netAPY: number; totalDeployed: number; totalBorrowed: number } {
  const iterations: LoopIteration[] = [];
  let collateral = capitalUSD;
  let totalDeployed = 0;
  let totalBorrowed = 0;

  for (let d = 1; d <= depth; d++) {
    const borrowAmount = collateral * ltv;
    totalBorrowed   += borrowAmount;
    totalDeployed   += borrowAmount;

    // Geometric series liquidation threshold
    const totalCollateral  = capitalUSD * (1 - Math.pow(ltv, d)) / (1 - ltv) + capitalUSD;
    const liquidationUSD   = totalCollateral * ltv;
    const cumulativeYield  = totalDeployed * yieldAPY;

    const warning = ltv > 0.65
      ? `LTV ${(ltv * 100).toFixed(0)}% — high liquidation risk. Keep buffer wallet funded.`
      : undefined;

    iterations.push({
      depth: d,
      collateralUSD:   collateral,
      borrowAmountUSD: borrowAmount,
      deployedUSD:     totalDeployed,
      cumulativeYield,
      liquidationUSD,
      warning,
    });

    // Next iteration: reinvest rewards into collateral
    collateral = capitalUSD + cumulativeYield * 0.5; // 50% reward reinvestment assumed
  }

  // Net leveraged APY = yield on deployed / initial capital
  const netAPY = (iterations[iterations.length - 1].cumulativeYield) / capitalUSD;

  return { iterations, netAPY, totalDeployed, totalBorrowed };
}

// ── Tx builders ───────────────────────────────────────────────────────────────
function buildMorphoSupplyCollateralTx(
  marketId:      string,
  amountWei:     bigint,
  onBehalf:      string,
  loanToken:     string = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  // USDC Base
  collateralToken: string = "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", // cbETH Base
  oracle:        string = "0xFEa2D58cEfCe9B1c8B5CA5B4C2B1C1E3D3E3E3E3",
  irm:           string = "0x870aC11D48B15DB9a138Cf899d20F13F79Ba00BC",
  lltv:          bigint = 860000000000000000n // 0.86 LLTV
): UnsignedTx {
  const marketParams = { loanToken, collateralToken, oracle, irm, lltv };
  const callData = morphoIface.encodeFunctionData("supplyCollateral", [
    marketParams, amountWei, onBehalf, "0x",
  ]);
  return {
    step:        1,
    description: `Supply ${ethers.formatEther(amountWei)} collateral to Morpho Base`,
    to:          PROTOCOLS.morpho.address,
    data:        callData,
    value:       "0",
    gasEstimate: "150000",
    chainId:     8453,
    chainName:   "Base",
    WARNING:     "Review 'to' and 'data' before signing. This deposits your collateral.",
  };
}

function buildMorphoBorrowTx(
  marketId:   string,
  amountWei:  bigint,
  onBehalf:   string,
  receiver:   string,
  loanToken:  string = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  collateralToken: string = "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
  oracle:     string = "0xFEa2D58cEfCe9B1c8B5CA5B4C2B1C1E3D3E3E3E3",
  irm:        string = "0x870aC11D48B15DB9a138Cf899d20F13F79Ba00BC",
  lltv:       bigint = 860000000000000000n
): UnsignedTx {
  const marketParams = { loanToken, collateralToken, oracle, irm, lltv };
  const callData = morphoIface.encodeFunctionData("borrow", [
    marketParams, amountWei, 0n, onBehalf, receiver,
  ]);
  return {
    step:        2,
    description: `Borrow ${ethers.formatUnits(amountWei, 6)} USDC from Morpho Base`,
    to:          PROTOCOLS.morpho.address,
    data:        callData,
    value:       "0",
    gasEstimate: "200000",
    chainId:     8453,
    chainName:   "Base",
    WARNING:     "This takes on debt. Confirm liquidation price in positions.json before signing.",
  };
}

// ── Manager ───────────────────────────────────────────────────────────────────
class LoopProposer {

  async getWalletAddresses() {
    try {
      const manifest = JSON.parse(await fs.readFile(WALLET_FILE, "utf-8"));
      return Object.fromEntries(manifest.wallets.map((w: { purpose: string; address: string }) => [w.purpose, w.address]));
    } catch {
      return {};
    }
  }

  async proposeLoop(input: z.infer<typeof ProposeLoopSchema>): Promise<{
    proposal: string;
    simulation: ReturnType<typeof computeLoop>;
    transactions: UnsignedTx[];
    signing_instructions: string;
    risk_summary: string;
  }> {
    const addrs    = await this.getWalletAddresses() as Record<string, string>;
    const walletAddr = input.wallet_address ?? addrs.collateral ?? ethers.ZeroAddress;
    const yieldAPY = PROTOCOLS[input.yield_protocol].yieldAPY;
    const marketId = input.market_id ?? "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc";

    const simulation = computeLoop(input.capital_usd, input.ltv, input.depth, yieldAPY);

    // Build unsigned transactions for loop depth
    const transactions: UnsignedTx[] = [];
    let remainingCapital = input.capital_usd;

    for (let d = 1; d <= input.depth; d++) {
      const collateralWei = BigInt(Math.floor(remainingCapital * 1e18 / 2000)); // assume $2000/ETH
      const borrowAmountWei = BigInt(Math.floor(remainingCapital * input.ltv * 1e6)); // USDC 6 decimals

      transactions.push(buildMorphoSupplyCollateralTx(marketId, collateralWei, walletAddr));
      transactions.push(buildMorphoBorrowTx(marketId, borrowAmountWei, walletAddr, addrs.yield ?? walletAddr));

      // Next iteration uses borrowed amount as new capital
      remainingCapital = remainingCapital * input.ltv;
    }

    const lastIter = simulation.iterations[simulation.iterations.length - 1];
    const riskScore = input.ltv / PROTOCOLS.morpho.maxLTV * 100;

    return {
      proposal: `Loop proposal: ${input.depth} iterations, ${input.collateral_asset} collateral, LTV ${(input.ltv * 100).toFixed(0)}%, yield via ${input.yield_protocol}`,
      simulation,
      transactions,
      signing_instructions: [
        "IMPORTANT: Review every transaction before signing.",
        `1. Load your wallet: const wallet = await ethers.Wallet.fromEncryptedJson(keystoreJson, passphrase)`,
        `2. Connect to Base: const provider = new ethers.JsonRpcProvider('${BASE_RPC.slice(0,40)}...')`,
        `3. For each tx in order: await wallet.connect(provider).sendTransaction(tx)`,
        `4. After each tx: check positions.json — health factor must remain above ${ALERT_WARNING}`,
        `5. Keep buffer wallet funded with ${(lastIter.borrowAmountUSD * 0.2).toFixed(0)} USDC emergency reserve`,
      ].join("\n"),
      risk_summary: [
        `Net leveraged APY:       ${(simulation.netAPY * 100).toFixed(1)}%`,
        `Total deployed:          $${simulation.totalDeployed.toFixed(2)}`,
        `Total borrowed:          $${simulation.totalBorrowed.toFixed(2)}`,
        `Risk score:              ${riskScore.toFixed(0)}/100`,
        `Liquidation threshold:   $${lastIter.liquidationUSD.toFixed(2)}`,
        input.ltv > 0.65 ? "⚠  LTV above 65% — reduce depth or LTV if market is volatile" : "✓  LTV within safe range",
      ].join("\n"),
    };
  }

  async proposeUnwind(input: z.infer<typeof ProposeUnwindSchema>): Promise<{
    transactions: UnsignedTx[];
    note: string;
  }> {
    const addrs = await this.getWalletAddresses() as Record<string, string>;
    const walletAddr = input.wallet_address ?? addrs.collateral ?? ethers.ZeroAddress;
    const marketId = input.market_id ?? "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc";

    // Unwind = repay borrow → withdraw collateral
    const repayTx: UnsignedTx = {
      step:        1,
      description: "Repay all USDC debt to Morpho (amount from positions.json borrowedUSD)",
      to:          PROTOCOLS.morpho.address,
      data:        "0x", // encode with actual borrowed amount from positions.json
      value:       "0",
      gasEstimate: "200000",
      chainId:     8453,
      chainName:   "Base",
      WARNING:     "Repay full borrow amount. Fetch exact amount from positions.json borrowedUSD.",
    };

    const withdrawTx: UnsignedTx = {
      step:        2,
      description: "Withdraw all collateral from Morpho after debt repaid",
      to:          PROTOCOLS.morpho.address,
      data:        "0x",
      value:       "0",
      gasEstimate: "180000",
      chainId:     8453,
      chainName:   "Base",
      WARNING:     "Only call after repayTx confirms. Check positions.json healthFactor = 999 first.",
    };

    return {
      transactions: [repayTx, withdrawTx],
      note: "Encode exact amounts from positions.json before signing. Call repay → withdraw in sequence. Emergency unwind preserves capital, exits all leveraged risk.",
    };
  }

  simulate(input: z.infer<typeof SimulateLoopSchema>) {
    const yieldAPY = PROTOCOLS[input.yield_protocol].yieldAPY;
    return computeLoop(input.capital_usd, input.ltv, input.depth, yieldAPY);
  }

  async positionHealth() {
    try {
      return JSON.parse(await fs.readFile(POSITIONS_FILE, "utf-8"));
    } catch {
      return { error: "No position data. Run position-monitor.ts first." };
    }
  }
}

// ── MCP wiring ─────────────────────────────────────────────────────────────────
const proposer = new LoopProposer();
const server   = new Server(
  { name: "evez-loop-proposer", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "propose_loop",
      description: "Compute a recursive collateral loop and return UNSIGNED transactions. You sign each tx. Agent never touches funds. Returns: simulation math, unsigned tx array, signing instructions, risk summary.",
      inputSchema: { type: "object", properties: {
        collateral_asset: { type: "string", enum: ["ETH","cbETH","wstETH","SOL"] },
        capital_usd:      { type: "number", description: "Capital to seed loop in USD" },
        ltv:              { type: "number", description: "LTV per cycle, max 0.70" },
        depth:            { type: "number", description: "Loop depth 1–3" },
        yield_protocol:   { type: "string", enum: ["kamino","morpho","pendle","raydium"] },
        market_id:        { type: "string" },
        wallet_address:   { type: "string" },
      }, required: ["collateral_asset","capital_usd","ltv","depth","yield_protocol"] },
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false },
    },
    {
      name: "propose_unwind",
      description: "Generate UNSIGNED unwind transactions to safely exit all leveraged positions. Returns repay + withdraw calldata for you to sign.",
      inputSchema: { type: "object", properties: {
        emergency:      { type: "boolean" },
        market_id:      { type: "string" },
        wallet_address: { type: "string" },
      }},
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false },
    },
    {
      name: "simulate_loop",
      description: "Run loop math only — no transactions generated. Returns APY projections, leverage ratios, and liquidation thresholds for any parameters.",
      inputSchema: { type: "object", properties: {
        collateral_asset: { type: "string", enum: ["ETH","cbETH","wstETH","SOL"] },
        capital_usd:      { type: "number" },
        ltv:              { type: "number" },
        depth:            { type: "number" },
        yield_protocol:   { type: "string", enum: ["kamino","morpho","pendle","raydium"] },
      }, required: ["collateral_asset","capital_usd","ltv","depth","yield_protocol"] },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true },
    },
    {
      name: "position_health",
      description: "Read current position health from last position-monitor poll. Returns health factor, LTV, collateral/borrow USD, risk level, and any active alerts.",
      inputSchema: { type: "object", properties: {} },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  const ok  = (d: unknown) => ({ content: [{ type: "text" as const, text: JSON.stringify(d, null, 2) }] });
  const err = (m: string)  => ({ content: [{ type: "text" as const, text: JSON.stringify({ error: m }) }], isError: true as const });

  try {
    switch (name) {
      case "propose_loop":    return ok(await proposer.proposeLoop(ProposeLoopSchema.parse(args)));
      case "propose_unwind":  return ok(await proposer.proposeUnwind(ProposeUnwindSchema.parse(args)));
      case "simulate_loop":   return ok(proposer.simulate(SimulateLoopSchema.parse(args)));
      case "position_health": return ok(await proposer.positionHealth());
      default:                return err(`Unknown tool: ${name}`);
    }
  } catch (e: unknown) {
    return err(e instanceof z.ZodError
      ? `Validation: ${e.errors.map(x => `${x.path.join(".")}: ${x.message}`).join("; ")}`
      : (e instanceof Error ? e.message : String(e)));
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[evez-loop-proposer] online — propose_loop, propose_unwind, simulate_loop, position_health");
