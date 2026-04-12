// position-monitor.ts — EVEZ-OS Position Monitor
// READ-ONLY chain state polling. No signing. No fund movement.
// Polls Morpho (Base), Kamino (Solana), EigenLayer (Ethereum) every POLL_MS.
// Writes positions to ~/.evez-os/positions.json
// Fires alerts to ~/.evez-os/alerts.json when health factor degrades.
//
// Run: npx tsx position-monitor.ts
// Env: ALCHEMY_BASE_URL, ALCHEMY_ETH_URL, SOLANA_RPC_URL

import { ethers } from "ethers";
import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";

// ── Config ─────────────────────────────────────────────────────────────────────
const EVEZ_DIR       = path.join(os.homedir(), ".evez-os");
const POSITIONS_FILE = path.join(EVEZ_DIR, "positions.json");
const ALERTS_FILE    = path.join(EVEZ_DIR, "alerts.json");
const WALLET_FILE    = path.join(EVEZ_DIR, "wallets.json");
const POLL_MS        = parseInt(process.env.POLL_MS ?? "60000", 10);

const BASE_RPC = process.env.ALCHEMY_BASE_URL ?? "https://mainnet.base.org";
const ETH_RPC  = process.env.ALCHEMY_ETH_URL  ?? "https://eth.llamarpc.com";
const SOL_RPC  = process.env.SOLANA_RPC_URL   ?? "https://api.mainnet-beta.solana.com";

// ── Alert thresholds ───────────────────────────────────────────────────────────
const ALERT_WARNING  = 1.5;   // HF below this → warning alert
const ALERT_CRITICAL = 1.2;   // HF below this → emergency unwind proposal
const LTV_MAX        = 0.70;  // LTV above this → alert regardless of HF

// ── Morpho Base ABIs (minimal — read-only calls only) ─────────────────────────
// Morpho Blue: https://github.com/morpho-org/morpho-blue
const MORPHO_BLUE_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"; // Base
const MORPHO_ABI = [
  "function position(bytes32 marketId, address user) view returns (uint256 supplyShares, uint128 borrowShares, uint128 collateral)",
  "function market(bytes32 marketId) view returns (uint128 totalSupplyAssets, uint128 totalSupplyShares, uint128 totalBorrowAssets, uint128 totalBorrowShares, uint128 lastUpdate, uint128 fee)",
  "function idToMarketParams(bytes32 marketId) view returns (address loanToken, address collateralToken, address oracle, address irm, uint256 lltv)",
];

// Chainlink oracle ABI (for asset prices)
const ORACLE_ABI = ["function latestAnswer() view returns (int256)", "function decimals() view returns (uint8)"];

// EigenLayer delegation manager
const EIGEN_DELEGATION = "0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37B"; // Ethereum mainnet
const EIGEN_ABI = ["function stakerOptedIntoLiquidStaking(address staker) view returns (bool)", "function operatorShares(address operator, address strategy) view returns (uint256)"];

// ── Types ─────────────────────────────────────────────────────────────────────
interface MorphoPosition {
  marketId:          string;
  collateralUSD:     number;
  borrowedUSD:       number;
  healthFactor:      number;
  currentLTV:        number;
  liquidationLTV:    number;
  liquidationPriceUSD: number;
  availableToBorrow: number;
  lastUpdated:       string;
}

interface KaminoPosition {
  vault:          string;
  depositedUSDC:  number;
  pendingRewards: number;
  estimatedAPY:   number;
  lastUpdated:    string;
}

interface EigenPosition {
  restaked:    number;
  avsYield:    number;
  weETHValue:  number;
  lastUpdated: string;
}

interface PositionSnapshot {
  ts:       string;
  morpho:   MorphoPosition | null;
  kamino:   KaminoPosition | null;
  eigen:    EigenPosition  | null;
  netAPY:   number;
  totalUSD: number;
  riskLevel: "safe" | "warning" | "critical";
}

interface Alert {
  ts:       string;
  level:    "warning" | "critical";
  type:     string;
  message:  string;
  data:     Record<string, unknown>;
  resolved: boolean;
}

// ── Providers ─────────────────────────────────────────────────────────────────
const baseProvider = new ethers.JsonRpcProvider(BASE_RPC);
const ethProvider  = new ethers.JsonRpcProvider(ETH_RPC);

// ── Load wallet addresses ──────────────────────────────────────────────────────
async function getAddresses(): Promise<{ collateral: string; yield: string; arb: string; buffer: string }> {
  try {
    const manifest = JSON.parse(await fs.readFile(WALLET_FILE, "utf-8"));
    const byPurpose = Object.fromEntries(manifest.wallets.map((w: { purpose: string; address: string }) => [w.purpose, w.address]));
    return byPurpose as { collateral: string; yield: string; arb: string; buffer: string };
  } catch {
    // Fallback: read from env or return zero addresses for monitoring setup
    return {
      collateral: process.env.COLLATERAL_ADDR ?? ethers.ZeroAddress,
      yield:      process.env.YIELD_ADDR      ?? ethers.ZeroAddress,
      arb:        process.env.ARB_ADDR        ?? ethers.ZeroAddress,
      buffer:     process.env.BUFFER_ADDR     ?? ethers.ZeroAddress,
    };
  }
}

// ── Morpho position fetch ──────────────────────────────────────────────────────
async function fetchMorphoPosition(walletAddress: string, marketId: string): Promise<MorphoPosition | null> {
  if (walletAddress === ethers.ZeroAddress) return null;
  try {
    const morpho = new ethers.Contract(MORPHO_BLUE_ADDRESS, MORPHO_ABI, baseProvider);

    const [pos, marketParams] = await Promise.all([
      morpho.position(marketId, walletAddress),
      morpho.idToMarketParams(marketId),
    ]);

    const { supplyShares, borrowShares, collateral } = pos;
    const lltv = Number(marketParams.lltv) / 1e18; // normalized

    // Fetch oracle price for collateral asset
    const oracle     = new ethers.Contract(marketParams.oracle, ORACLE_ABI, baseProvider);
    const [price, dec] = await Promise.all([oracle.latestAnswer(), oracle.decimals()]);
    const priceUSD   = Number(price) / Math.pow(10, Number(dec));

    const collateralUSD     = (Number(collateral) / 1e18) * priceUSD;
    const borrowedUSD       = (Number(borrowShares) / 1e18); // simplified — shares need price calculation
    const healthFactor      = borrowedUSD > 0 ? (collateralUSD * lltv) / borrowedUSD : 999;
    const currentLTV        = collateralUSD > 0 ? borrowedUSD / collateralUSD : 0;
    const liquidationPriceUSD = borrowedUSD > 0 ? borrowedUSD / (Number(collateral) / 1e18 * lltv) : 0;
    const availableToBorrow   = Math.max(0, collateralUSD * lltv - borrowedUSD);

    return {
      marketId,
      collateralUSD,
      borrowedUSD,
      healthFactor,
      currentLTV,
      liquidationLTV: lltv,
      liquidationPriceUSD,
      availableToBorrow,
      lastUpdated: new Date().toISOString(),
    };
  } catch (e) {
    console.error("[morpho] fetch error:", e instanceof Error ? e.message : e);
    return null;
  }
}

// ── Kamino position fetch (Solana — via RPC) ──────────────────────────────────
async function fetchKaminoPosition(solanaAddress: string, vaultAddress: string): Promise<KaminoPosition | null> {
  if (!solanaAddress || solanaAddress.length < 32) return null;
  try {
    // Solana JSON-RPC — getTokenAccountsByOwner for Kamino vault shares
    const resp = await fetch(SOL_RPC, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0", id: 1,
        method: "getTokenAccountsByOwner",
        params: [
          solanaAddress,
          { programId: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" },
          { encoding: "jsonParsed" },
        ],
      }),
    });
    const data = await resp.json() as { result: { value: Array<{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: number } } } } } }> } };
    // For each token account, check if mint matches Kamino vault shares mint
    // This is simplified — production version queries Kamino's on-chain strategy account
    const tokenAccounts = data.result?.value ?? [];
    const totalBalance  = tokenAccounts.reduce((sum: number, acc: { account: { data: { parsed: { info: { tokenAmount: { uiAmount: number } } } } } }) => {
      return sum + (acc.account?.data?.parsed?.info?.tokenAmount?.uiAmount ?? 0);
    }, 0);

    return {
      vault:          vaultAddress,
      depositedUSDC:  totalBalance,
      pendingRewards: totalBalance * 0.001, // estimated — query Kamino API for exact
      estimatedAPY:   0.28, // Kamino USDC vault approximate March 2026
      lastUpdated:    new Date().toISOString(),
    };
  } catch (e) {
    console.error("[kamino] fetch error:", e instanceof Error ? e.message : e);
    return null;
  }
}

// ── EigenLayer fetch ──────────────────────────────────────────────────────────
async function fetchEigenPosition(walletAddress: string): Promise<EigenPosition | null> {
  if (walletAddress === ethers.ZeroAddress) return null;
  try {
    // stETH strategy address on EigenLayer
    const stETH_STRATEGY = "0x93c4b944D05dfe6df7645A86cd2206016c51564D";
    const eigen = new ethers.Contract(EIGEN_DELEGATION, EIGEN_ABI, ethProvider);
    const shares = await eigen.operatorShares(walletAddress, stETH_STRATEGY);
    const restakedETH = Number(shares) / 1e18;

    // Approximate values
    const weETHValue = restakedETH * 1.065; // ~6.5% EigenLayer boost
    const avsYield   = restakedETH * 0.06;  // ~6% AVS yield per year

    return {
      restaked:   restakedETH,
      avsYield,
      weETHValue,
      lastUpdated: new Date().toISOString(),
    };
  } catch (e) {
    console.error("[eigenlayer] fetch error:", e instanceof Error ? e.message : e);
    return null;
  }
}

// ── Alert system ───────────────────────────────────────────────────────────────
async function fireAlert(level: Alert["level"], type: string, message: string, data: Record<string, unknown>) {
  console.error(`\n⚠  [ALERT:${level.toUpperCase()}] ${message}`);

  const alert: Alert = {
    ts: new Date().toISOString(), level, type, message, data, resolved: false,
  };

  let alerts: Alert[] = [];
  try {
    alerts = JSON.parse(await fs.readFile(ALERTS_FILE, "utf-8"));
  } catch { /* first alert */ }

  alerts.unshift(alert);
  alerts = alerts.slice(0, 500); // keep last 500
  await fs.writeFile(ALERTS_FILE, JSON.stringify(alerts, null, 2));

  // Also emit to EVEZ event spine format
  console.error(JSON.stringify({
    event: level === "critical" ? "FIRE_LIQUIDATION_RISK" : "FIRE_POSITION_WARNING",
    payload: { level, type, message, ...data },
    ts: alert.ts,
  }));
}

// ── Main poll tick ─────────────────────────────────────────────────────────────
async function pollTick() {
  const addrs = await getAddresses();

  // Known Morpho Base market IDs — update with your actual markets
  const MORPHO_USDC_ETH_MARKET = process.env.MORPHO_MARKET_ID
    ?? "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"; // wstETH/USDC

  const [morpho, kamino, eigen] = await Promise.all([
    fetchMorphoPosition(addrs.collateral, MORPHO_USDC_ETH_MARKET),
    fetchKaminoPosition(process.env.SOLANA_WALLET_ADDR ?? "", process.env.KAMINO_VAULT ?? ""),
    fetchEigenPosition(addrs.collateral),
  ]);

  // Calculate portfolio totals
  const morphoUSD  = (morpho?.collateralUSD ?? 0) - (morpho?.borrowedUSD ?? 0);
  const kaminoUSD  = kamino?.depositedUSDC ?? 0;
  const eigenUSD   = (eigen?.weETHValue ?? 0) * (parseFloat(process.env.ETH_PRICE ?? "2000"));
  const totalUSD   = morphoUSD + kaminoUSD + eigenUSD;

  // Net APY estimate
  const netAPY = (
    (morpho ? 0.15 : 0)    // Morpho supply APY
    + (kamino ? 0.28 : 0)  // Kamino vault APY
    + (eigen  ? 0.095 : 0) // EigenLayer staking + AVS
  ) / Math.max(1, [morpho, kamino, eigen].filter(Boolean).length);

  // Risk assessment
  let riskLevel: PositionSnapshot["riskLevel"] = "safe";
  if (morpho) {
    if (morpho.healthFactor < ALERT_CRITICAL || morpho.currentLTV > LTV_MAX) {
      riskLevel = "critical";
    } else if (morpho.healthFactor < ALERT_WARNING) {
      riskLevel = "warning";
    }
  }

  const snapshot: PositionSnapshot = {
    ts: new Date().toISOString(),
    morpho, kamino, eigen,
    netAPY, totalUSD, riskLevel,
  };

  // Write positions
  await fs.mkdir(EVEZ_DIR, { recursive: true });
  await fs.writeFile(POSITIONS_FILE, JSON.stringify(snapshot, null, 2));

  // Console summary
  const hf = morpho?.healthFactor.toFixed(3) ?? "N/A";
  const ltv = morpho ? `${(morpho.currentLTV * 100).toFixed(1)}%` : "N/A";
  console.log(
    `[${new Date().toISOString().slice(11, 19)}] ` +
    `HF:${hf}  LTV:${ltv}  Total:$${totalUSD.toFixed(2)}  APY:${(netAPY * 100).toFixed(1)}%  Risk:${riskLevel.toUpperCase()}`
  );

  // Fire alerts
  if (morpho && morpho.healthFactor < ALERT_CRITICAL) {
    await fireAlert("critical", "liquidation_imminent",
      `Health factor CRITICAL: ${morpho.healthFactor.toFixed(3)} — emergency unwind required`,
      { healthFactor: morpho.healthFactor, liquidationPrice: morpho.liquidationPriceUSD, marketId: morpho.marketId }
    );
  } else if (morpho && morpho.healthFactor < ALERT_WARNING) {
    await fireAlert("warning", "health_factor_low",
      `Health factor warning: ${morpho.healthFactor.toFixed(3)} — consider reducing position`,
      { healthFactor: morpho.healthFactor, currentLTV: morpho.currentLTV }
    );
  }

  if (morpho && morpho.currentLTV > LTV_MAX) {
    await fireAlert("warning", "ltv_exceeded",
      `LTV ${(morpho.currentLTV * 100).toFixed(1)}% exceeds max ${(LTV_MAX * 100).toFixed(0)}%`,
      { currentLTV: morpho.currentLTV, maxLTV: LTV_MAX }
    );
  }
}

// ── Boot ───────────────────────────────────────────────────────────────────────
await fs.mkdir(EVEZ_DIR, { recursive: true });
console.log(`[position-monitor] online | poll every ${POLL_MS / 1000}s | ALERT_WARNING HF<${ALERT_WARNING} | ALERT_CRITICAL HF<${ALERT_CRITICAL}`);
console.log(`[position-monitor] RPC Base:${BASE_RPC.slice(0, 30)}... ETH:${ETH_RPC.slice(0, 30)}...`);

await pollTick();
setInterval(pollTick, POLL_MS);
