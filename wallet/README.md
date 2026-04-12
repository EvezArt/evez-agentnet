# EVEZ Wallet Infrastructure

**Architecture: Human signs everything. Agents analyze and propose.**

The agent stack does: position monitoring, loop math, tx construction, risk alerts.  
You do: wallet decryption, transaction review, signing, broadcast.

No private key ever touches an agent, a server, a log file, or any network call.

---

## Setup (one-time)

```bash
cd evez-wallet
npm install
npm run wallet:init
```

This runs the interactive setup:
1. Generates a 24-word BIP-39 mnemonic — **write it on paper, store offline**
2. Derives 5 purpose-segregated wallets (4 EVM + 1 Solana)
3. Encrypts each to `~/.evez-os/keystores/*.keystore.json` with your passphrase
4. Saves addresses-only manifest to `~/.evez-os/wallets.json`

```bash
npm run wallet:show    # Print all addresses (no keys ever printed)
```

---

## Wallet layout

| Purpose | Derivation | Chain | Use |
|---|---|---|---|
| `collateral` | m/44'/60'/0'/0/0 | Base | Morpho deposits |
| `yield` | m/44'/60'/0'/0/1 | Base/Ethereum | Kamino/Pendle |
| `arb` | m/44'/60'/0'/0/2 | Ethereum | Flash loan receiver |
| `buffer` | m/44'/60'/0'/0/3 | Base | Emergency USDC reserve |
| `solana` | m/44'/501'/0'/0' | Solana | Kamino, Jupiter, Raydium |

---

## Running the stack

**Terminal 1 — Position monitor (read-only polling)**
```bash
# Set your RPCs
export ALCHEMY_BASE_URL="https://base-mainnet.g.alchemy.com/v2/YOUR_KEY"
export ALCHEMY_ETH_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
export SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"
export MORPHO_MARKET_ID="0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"

npm run monitor
```

Writes to `~/.evez-os/positions.json` every 60s.  
Fires alerts to `~/.evez-os/alerts.json` when HF < 1.5 (warning) or HF < 1.2 (critical).

**Terminal 2 — Loop proposer (MCP server)**
```bash
npm run proposer
```

Or add to Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "evez-loop-proposer": {
      "command": "node",
      "args": ["/path/to/evez-wallet/dist/loop-proposer.js"]
    }
  }
}
```

---

## The signing ceremony

The loop proposer returns `UnsignedTx[]`. You execute them:

```typescript
import { ethers } from "ethers";
import * as fs from "fs/promises";

// 1. Load your encrypted keystore
const ks = await fs.readFile(
  `${process.env.HOME}/.evez-os/keystores/collateral.keystore.json`,
  "utf-8"
);

// 2. Decrypt with your passphrase (only in memory, never logged)
const wallet = await ethers.Wallet.fromEncryptedJson(ks, process.env.WALLET_PASSPHRASE!);

// 3. Connect to Base
const provider = new ethers.JsonRpcProvider(process.env.ALCHEMY_BASE_URL!);
const signer   = wallet.connect(provider);

// 4. For each unsigned tx from propose_loop:
for (const tx of unsignedTxArray) {
  console.log(`\nReviewing: ${tx.description}`);
  console.log(`To:        ${tx.to}`);
  console.log(`Gas est:   ${tx.gasEstimate}`);
  console.log(`WARNING:   ${tx.WARNING}`);
  
  // YOU decide to proceed:
  const receipt = await signer.sendTransaction({
    to:       tx.to,
    data:     tx.data,
    value:    BigInt(tx.value),
    gasLimit: BigInt(tx.gasEstimate),
  });
  
  console.log(`Confirmed: ${receipt.hash}`);
  
  // Check health after each tx
  const positions = JSON.parse(
    await fs.readFile(`${process.env.HOME}/.evez-os/positions.json`, "utf-8")
  );
  if (positions.morpho?.healthFactor < 1.5) {
    console.error("⚠  Health factor below 1.5 — STOP and review before continuing");
    break;
  }
}
```

---

## MCP tools (via Claude)

| Tool | Type | What it does |
|---|---|---|
| `simulate_loop` | read-only | APY math, leverage ratios, liquidation prices — no tx |
| `propose_loop` | proposes txs | Returns unsigned tx array for you to sign |
| `propose_unwind` | proposes txs | Returns repay + withdraw txs to exit positions |
| `position_health` | read-only | Latest health factor, LTV, alerts from monitor |

---

## Critical rules

- **Never exceed 70% LTV.** The monitor alerts at 70%, proposes emergency unwind at HF < 1.2.
- **Keep buffer wallet funded.** Maintain 20% of total position value in `buffer` as USDC.
- **Sign one tx at a time.** Check `positions.json` health factor after each transaction.
- **Mnemonic offline only.** Never type it into any app, browser, or terminal that might log.
- **Passphrase ≠ mnemonic.** These are different. Both are required to reconstruct a wallet.

---

## File locations

```
~/.evez-os/
  wallets.json          ← addresses only (safe to read/share)
  positions.json        ← latest chain state (refreshed every 60s by monitor)
  alerts.json           ← liquidation risk alerts
  keystores/
    collateral.keystore.json  ← encrypted, requires passphrase
    yield.keystore.json
    arb.keystore.json
    buffer.keystore.json
    solana.keystore.json
```
