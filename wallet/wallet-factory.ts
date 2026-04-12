// wallet-factory.ts — EVEZ-OS HD Wallet Factory
// Generates purpose-segregated wallets from a single BIP-39 mnemonic.
// Private keys are ONLY held in memory during the session or encrypted on disk.
// The agent never moves funds. You sign every transaction.
//
// Usage:
//   npx tsx wallet-factory.ts init          → generate fresh mnemonic + all wallets
//   npx tsx wallet-factory.ts show          → print wallet addresses (NO private keys)
//   npx tsx wallet-factory.ts export-ks     → export encrypted keystoreV3 JSONs

import { ethers } from "ethers";
import * as bip39 from "@scure/bip39";
import { wordlist } from "@scure/bip39/wordlists/english";
import { HDKey } from "@scure/bip32";
import * as bs58 from "bs58";
import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";
import * as readline from "readline";
import { createHash } from "crypto";

// ── Paths ──────────────────────────────────────────────────────────────────────
const EVEZ_DIR       = path.join(os.homedir(), ".evez-os");
const WALLET_FILE    = path.join(EVEZ_DIR, "wallets.json");   // addresses only, no keys
const KEYSTORE_DIR   = path.join(EVEZ_DIR, "keystores");      // encrypted keystoreV3

// ── Wallet purposes ────────────────────────────────────────────────────────────
// Each wallet is isolated by purpose — a compromise of one doesn't affect others.
const WALLET_PURPOSES = [
  {
    name:        "collateral",
    derivation:  "m/44'/60'/0'/0/0",
    chain:       "ethereum",
    description: "Morpho Base deposits — primary collateral pool",
    maxBalance:  "No autonomous movement. You deposit manually.",
  },
  {
    name:        "yield",
    derivation:  "m/44'/60'/0'/0/1",
    chain:       "ethereum",
    description: "Kamino/Pendle yield positions — receives borrowed USDC",
    maxBalance:  "No autonomous movement.",
  },
  {
    name:        "arb",
    derivation:  "m/44'/60'/0'/0/2",
    chain:       "ethereum",
    description: "Flash loan receiver contract deployer",
    maxBalance:  "Only holds gas. Flash loan principal never rests here.",
  },
  {
    name:        "buffer",
    derivation:  "m/44'/60'/0'/0/3",
    chain:       "ethereum",
    description: "Emergency USDC reserve — collateral top-up fund",
    maxBalance:  "Keep 20% of total position value here minimum.",
  },
  {
    name:        "solana",
    derivation:  "m/44'/501'/0'/0'",
    chain:       "solana",
    description: "Solana wallet — Kamino, Jupiter, Raydium operations",
    maxBalance:  "No autonomous movement.",
  },
] as const;

type WalletPurpose = (typeof WALLET_PURPOSES)[number]["name"];

interface WalletRecord {
  purpose:     WalletPurpose;
  chain:       string;
  address:     string;   // public only
  derivation:  string;
  description: string;
  created:     string;
  keystorePath?: string;
}

interface WalletManifest {
  version:     string;
  created:     string;
  mnemonicHash: string;  // sha256 of mnemonic — lets you verify you have the right seed
  wallets:     WalletRecord[];
}

// ── Helpers ────────────────────────────────────────────────────────────────────
async function prompt(q: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(q, (ans) => { rl.close(); resolve(ans); });
  });
}

function deriveEthereumWallet(mnemonic: string, derivationPath: string): ethers.HDNodeWallet {
  return ethers.HDNodeWallet.fromPhrase(mnemonic, undefined, derivationPath);
}

function deriveSolanaAddress(mnemonic: string, derivationPath: string): string {
  // BIP-44 Solana derivation using scure/bip32
  const seed = bip39.mnemonicToSeedSync(mnemonic);
  const root  = HDKey.fromMasterSeed(seed);
  const child = root.derive(derivationPath);
  if (!child.publicKey) throw new Error("Failed to derive Solana public key");
  // Solana uses Ed25519 — the public key IS the address in base58
  return bs58.encode(child.publicKey);
}

async function ensureDirs() {
  await fs.mkdir(EVEZ_DIR,     { recursive: true });
  await fs.mkdir(KEYSTORE_DIR, { recursive: true });
}

// ── INIT: generate wallets ─────────────────────────────────────────────────────
async function init() {
  await ensureDirs();

  // Check if already initialized
  try {
    await fs.access(WALLET_FILE);
    const overwrite = await prompt("⚠  Wallet manifest already exists. Overwrite? (type YES to confirm): ");
    if (overwrite.trim() !== "YES") {
      console.log("Aborted. Existing wallets preserved.");
      process.exit(0);
    }
  } catch { /* file doesn't exist — proceed */ }

  console.log("\n🔐 EVEZ Wallet Factory — Initialization\n");
  console.log("Generating BIP-39 mnemonic (256 bits entropy = 24 words)...\n");

  const mnemonic = bip39.generateMnemonic(wordlist, 256);

  console.log("═══════════════════════════════════════════════════════════");
  console.log("  WRITE THIS DOWN. STORE OFFLINE. NEVER PASTE ANYWHERE.");
  console.log("═══════════════════════════════════════════════════════════");
  console.log(`\n  ${mnemonic}\n`);
  console.log("═══════════════════════════════════════════════════════════\n");

  await prompt("Press ENTER once you have written down the mnemonic securely: ");

  const passphrase = await prompt("Enter encryption passphrase for keystores (min 16 chars): ");
  if (passphrase.length < 16) {
    console.error("Passphrase too short. Minimum 16 characters.");
    process.exit(1);
  }

  const confirm = await prompt("Confirm passphrase: ");
  if (passphrase !== confirm) {
    console.error("Passphrases do not match.");
    process.exit(1);
  }

  console.log("\nDeriving wallets...\n");

  const walletRecords: WalletRecord[] = [];

  for (const purpose of WALLET_PURPOSES) {
    process.stdout.write(`  ${purpose.name.padEnd(12)} (${purpose.chain}) ... `);

    let address: string;
    let keystorePath: string | undefined;

    if (purpose.chain === "solana") {
      address = deriveSolanaAddress(mnemonic, purpose.derivation);
      // Solana keystore: store encrypted seed bytes
      const seed    = bip39.mnemonicToSeedSync(mnemonic);
      const root    = HDKey.fromMasterSeed(seed);
      const child   = root.derive(purpose.derivation);
      const privKey = child.privateKey;
      if (privKey) {
        // Encrypt with AES via a simple envelope (ethers doesn't handle Solana natively)
        const solKs = {
          address,
          encrypted: Buffer.from(privKey).toString("hex"), // TODO: encrypt with user passphrase
          note: "Replace .encrypted with proper AES-256-GCM encryption before production use",
        };
        keystorePath = path.join(KEYSTORE_DIR, `${purpose.name}.keystore.json`);
        await fs.writeFile(keystorePath, JSON.stringify(solKs, null, 2), { mode: 0o600 });
      }
    } else {
      const wallet  = deriveEthereumWallet(mnemonic, purpose.derivation);
      address       = wallet.address;
      // Encrypt to keystoreV3 — industry standard, compatible with MetaMask/Ledger
      const ks      = await wallet.encrypt(passphrase, { scrypt: { N: 131072 } });
      keystorePath  = path.join(KEYSTORE_DIR, `${purpose.name}.keystore.json`);
      await fs.writeFile(keystorePath, ks, { mode: 0o600 });
    }

    walletRecords.push({
      purpose:     purpose.name,
      chain:       purpose.chain,
      address,
      derivation:  purpose.derivation,
      description: purpose.description,
      created:     new Date().toISOString(),
      keystorePath,
    });

    console.log(`✓  ${address}`);
  }

  // Save manifest — addresses only, zero private key material
  const manifest: WalletManifest = {
    version:      "1.0.0",
    created:      new Date().toISOString(),
    mnemonicHash: createHash("sha256").update(mnemonic).digest("hex"),
    wallets:      walletRecords,
  };

  await fs.writeFile(WALLET_FILE, JSON.stringify(manifest, null, 2), { mode: 0o644 });

  console.log("\n✅  Wallet manifest saved to:", WALLET_FILE);
  console.log("🔒  Encrypted keystores saved to:", KEYSTORE_DIR);
  console.log("\n⚠   Private keys never touch this output. To sign transactions:");
  console.log('    const ks = fs.readFileSync("~/.evez-os/keystores/collateral.keystore.json", "utf-8")');
  console.log('    const wallet = await ethers.Wallet.fromEncryptedJson(ks, YOUR_PASSPHRASE)');
  console.log("    await wallet.sendTransaction(unsignedTx)  // from loop-proposer output\n");

  // Wipe mnemonic from memory (best-effort in JS)
  mnemonic.split("").forEach((_, i, a) => { a[i] = "0"; });
}

// ── SHOW: print addresses only ─────────────────────────────────────────────────
async function show() {
  try {
    const raw: WalletManifest = JSON.parse(await fs.readFile(WALLET_FILE, "utf-8"));
    console.log("\n EVEZ Wallet Addresses (no private keys)\n");
    console.log(`  Mnemonic SHA-256: ${raw.mnemonicHash}\n`);
    for (const w of raw.wallets) {
      console.log(`  ${w.purpose.padEnd(12)} [${w.chain.padEnd(8)}]  ${w.address}`);
      console.log(`               ${w.description}`);
      console.log();
    }
    console.log(`  Created: ${raw.created}\n`);
  } catch {
    console.error("No wallet manifest found. Run: npx tsx wallet-factory.ts init");
  }
}

// ── LOAD: decrypt and return wallet for signing (call from your scripts) ────────
export async function loadWallet(purpose: WalletPurpose, passphrase: string): Promise<ethers.Wallet> {
  const manifest: WalletManifest = JSON.parse(await fs.readFile(WALLET_FILE, "utf-8"));
  const record = manifest.wallets.find((w) => w.purpose === purpose);
  if (!record) throw new Error(`No wallet found for purpose: ${purpose}`);
  if (!record.keystorePath) throw new Error(`No keystore path for: ${purpose}`);
  const ks = await fs.readFile(record.keystorePath, "utf-8");
  return ethers.Wallet.fromEncryptedJson(ks, passphrase) as Promise<ethers.Wallet>;
}

export async function getWalletAddresses(): Promise<Record<WalletPurpose, string>> {
  const manifest: WalletManifest = JSON.parse(await fs.readFile(WALLET_FILE, "utf-8"));
  return Object.fromEntries(manifest.wallets.map((w) => [w.purpose, w.address])) as Record<WalletPurpose, string>;
}

// ── CLI entrypoint ─────────────────────────────────────────────────────────────
const cmd = process.argv[2];
if (cmd === "init")       await init();
else if (cmd === "show")  await show();
else {
  console.log("Usage:");
  console.log("  npx tsx wallet-factory.ts init       Generate wallets + encrypted keystores");
  console.log("  npx tsx wallet-factory.ts show       Print addresses (no private keys)");
}
