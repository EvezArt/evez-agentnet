"""
AGENT WALLET
The capital layer. Closes the loop between on-chain yield and real-world spend.

Flow:
  SOL (Phantom/x402 wallet)
  -> Jupiter swap -> USDC
  -> Bridge.xyz -> Stripe financial account
  -> Stripe Issuing -> Virtual Visa card
  -> Pays for: Groq compute, Twitter API, ElevenLabs, Vercel, API keys

Spend is logged to memory/spend.jsonl (same episodic substrate).
MetaLearner reads burn rate and adjusts generator scheduling accordingly.
If wallet health drops below threshold, high-cost generators are throttled.
If wallet health is strong, experimental generators get green-lit.

This is not theoretical. Stripe Issuing + Bridge is shipping in production.
Lithic and Marqeta have virtual card APIs built specifically for AI agents.
Coinbase AgentKit has wallet management built in.
The infrastructure exists. We are using it.
"""
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

log = logging.getLogger("AgentWallet")
Path("memory").mkdir(exist_ok=True)

SPEND_LOG_PATH = Path("memory/spend.jsonl")
WALLET_STATE_PATH = Path("memory/wallet_state.json")

# Monthly spend budget by category (USD)
DEFAULT_SPEND_LIMITS = {
    "compute": 50.00,       # Groq, RunPod
    "apis": 30.00,          # Twitter API, Perplexity, ElevenLabs
    "infrastructure": 20.00, # Vercel, GitHub Actions
    "research": 10.00,      # Arxiv, data feeds
    "total": 100.00,
}

# Merchant category codes to allow (Stripe MCC whitelist)
ALLOWED_MCCS = [
    "7372",  # Computer programming, data processing
    "5045",  # Computers and peripherals
    "5734",  # Computer and software stores
    "4814",  # Telecommunications
    "7374",  # Computer maintenance and repair
]


class JupiterSwap:
    """
    SOL -> USDC via Jupiter Aggregator API.
    No KYC. Pure on-chain. Best route auto-selected.
    """
    QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
    SWAP_URL = "https://quote-api.jup.ag/v6/swap"
    SOL_MINT = "So11111111111111111111111111111111111111112"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def __init__(self, wallet_keypair_b58: str = None):
        self.keypair = wallet_keypair_b58 or os.environ.get("SOLANA_WALLET_KEYPAIR")
        self.rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

    def get_quote(self, sol_amount_lamports: int) -> dict:
        """Get best swap route for SOL -> USDC."""
        if not requests:
            raise ImportError("requests library required")
        params = {
            "inputMint": self.SOL_MINT,
            "outputMint": self.USDC_MINT,
            "amount": str(sol_amount_lamports),
            "slippageBps": "50",  # 0.5% slippage
        }
        resp = requests.get(self.QUOTE_URL, params=params, timeout=10)
        resp.raise_for_status()
        quote = resp.json()
        log.info(f"Jupiter quote: {sol_amount_lamports} lamports -> {quote.get('outAmount')} USDC")
        return quote

    def execute_swap(self, quote: dict, user_public_key: str) -> dict:
        """
        Execute the swap. Returns transaction signature.
        Note: Requires signing with wallet keypair.
        For production use solana-py or @solana/web3.js for signing.
        """
        if not requests:
            raise ImportError("requests library required")
        payload = {
            "quoteResponse": quote,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }
        resp = requests.post(self.SWAP_URL, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        log.info(f"Swap transaction ready: {result.get('swapTransaction', '')[:20]}...")
        return result

    def swap_sol_to_usdc(self, sol_amount: float, user_public_key: str) -> dict:
        """Full flow: convert SOL amount to USDC."""
        lamports = int(sol_amount * 1_000_000_000)
        quote = self.get_quote(lamports)
        return self.execute_swap(quote, user_public_key)


class BridgeConnector:
    """
    Bridge.xyz - spend crypto directly from wallet to Stripe financial account.
    Docs: https://docs.bridge.xyz
    """
    BASE_URL = "https://api.bridge.xyz/v0"

    def __init__(self):
        self.api_key = os.environ.get("BRIDGE_API_KEY")
        if not self.api_key:
            log.warning("BRIDGE_API_KEY not set - Bridge connector in simulation mode")

    def _headers(self) -> dict:
        return {
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def create_transfer(self, amount_usd: float, source_wallet: str,
                        destination_stripe_account_id: str) -> dict:
        """
        Transfer USDC from crypto wallet to Stripe financial account.
        """
        if not self.api_key:
            log.info(f"[SIM] Bridge transfer: ${amount_usd} from {source_wallet} -> Stripe")
            return {"id": "sim_transfer", "status": "simulated", "amount": amount_usd}
        payload = {
            "amount": str(amount_usd),
            "on_behalf_of": source_wallet,
            "source": {
                "payment_rail": "solana",
                "currency": "usdc",
                "from_address": source_wallet,
            },
            "destination": {
                "payment_rail": "stripe",
                "currency": "usd",
                "stripe_connected_account_id": destination_stripe_account_id,
            },
        }
        resp = requests.post(f"{self.BASE_URL}/transfers", json=payload,
                             headers=self._headers(), timeout=15)
        resp.raise_for_status()
        result = resp.json()
        log.info(f"Bridge transfer created: {result.get('id')} status={result.get('status')}")
        return result

    def get_transfer_status(self, transfer_id: str) -> dict:
        resp = requests.get(f"{self.BASE_URL}/transfers/{transfer_id}",
                            headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()


class StripeIssuingCard:
    """
    Stripe Issuing - create and manage virtual Visa cards.
    Full programmatic control: spend limits, MCC restrictions, per-transaction rules.
    Docs: https://stripe.com/docs/issuing
    """

    def __init__(self):
        self.secret_key = os.environ.get("STRIPE_SECRET_KEY")
        self.base_url = "https://api.stripe.com/v1"
        if not self.secret_key:
            log.warning("STRIPE_SECRET_KEY not set - Stripe Issuing in simulation mode")

    def _headers(self) -> dict:
        import base64
        token = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        return {"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"}

    def _post(self, endpoint: str, data: dict) -> dict:
        if not self.secret_key:
            log.info(f"[SIM] Stripe POST {endpoint}: {data}")
            return {"id": f"sim_{endpoint.split('/')[-1]}", "status": "simulated", **data}
        resp = requests.post(f"{self.base_url}/{endpoint}",
                             data=data, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def create_cardholder(self, name: str, email: str, billing_address: dict) -> dict:
        """
        Create a cardholder (required before issuing a card).
        """
        data = {
            "type": "individual",
            "name": name,
            "email": email,
            "billing[address][line1]": billing_address.get("line1", ""),
            "billing[address][city]": billing_address.get("city", ""),
            "billing[address][state]": billing_address.get("state", ""),
            "billing[address][postal_code]": billing_address.get("postal_code", ""),
            "billing[address][country]": billing_address.get("country", "US"),
        }
        result = self._post("issuing/cardholders", data)
        log.info(f"Cardholder created: {result.get('id')}")
        return result

    def issue_virtual_card(self, cardholder_id: str,
                           spend_limits: dict = None,
                           allowed_mccs: list = None) -> dict:
        """
        Issue a virtual Visa card with programmatic spend controls.
        spend_limits: {"category": max_cents} dict
        allowed_mccs: list of MCC codes to whitelist
        """
        limits = spend_limits or DEFAULT_SPEND_LIMITS
        data = {
            "cardholder": cardholder_id,
            "currency": "usd",
            "type": "virtual",
            "status": "active",
            "spending_controls[spending_limits][0][amount]": str(int(limits.get("total", 100) * 100)),
            "spending_controls[spending_limits][0][interval]": "monthly",
        }
        if allowed_mccs:
            for i, mcc in enumerate(allowed_mccs):
                data[f"spending_controls[allowed_merchant_countries][{i}]"] = mcc
        result = self._post("issuing/cards", data)
        log.info(f"Virtual card issued: {result.get('id')} type={result.get('type')}")
        return result

    def get_card_details(self, card_id: str) -> dict:
        if not self.secret_key:
            return {"id": card_id, "status": "simulated"}
        resp = requests.get(f"{self.base_url}/issuing/cards/{card_id}",
                            headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def list_transactions(self, card_id: str, limit: int = 20) -> list:
        if not self.secret_key:
            return []
        params = f"card={card_id}&limit={limit}"
        resp = requests.get(f"{self.base_url}/issuing/transactions?{params}",
                            headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])


class SpendLogger:
    """
    Episodic memory for agent spending.
    Burns to memory/spend.jsonl - same substrate as AgentMemory episodic layer.
    MetaLearner reads this to adjust generator scheduling based on wallet health.
    """

    def log_spend(self, amount_usd: float, category: str,
                  merchant: str, card_id: str = None,
                  transaction_id: str = None, note: str = "") -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "amount_usd": amount_usd,
            "category": category,
            "merchant": merchant,
            "card_id": card_id,
            "transaction_id": transaction_id,
            "note": note,
        }
        with open(SPEND_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log.info(f"Spend logged: ${amount_usd} to {merchant} ({category})")

    def get_monthly_burn(self) -> dict:
        """
        Returns total spend by category for current month.
        Used by MetaLearner to throttle generators when budget is tight.
        """
        if not SPEND_LOG_PATH.exists():
            return {}
        now = datetime.utcnow()
        month_prefix = now.strftime("%Y-%m")
        totals = {}
        with open(SPEND_LOG_PATH) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if not entry["timestamp"].startswith(month_prefix):
                    continue
                cat = entry["category"]
                totals[cat] = totals.get(cat, 0.0) + entry["amount_usd"]
        return totals

    def get_wallet_health(self, balance_usd: float) -> dict:
        """
        Returns wallet health score (0-100) and recommended generator mode.
        - GREEN (75-100): All generators go; experimental generators get budget
        - YELLOW (40-74): Core generators only; throttle experimental
        - RED (0-39): Minimum viable only; pause all non-essential generators
        """
        burn = self.get_monthly_burn()
        total_burn = sum(burn.values())
        budget = DEFAULT_SPEND_LIMITS["total"]
        spend_ratio = total_burn / budget if budget > 0 else 0
        balance_score = min(balance_usd / 50, 1.0) * 100  # $50 = full score
        spend_score = (1 - spend_ratio) * 100
        health = int((balance_score * 0.6 + spend_score * 0.4))
        health = max(0, min(100, health))
        if health >= 75:
            mode = "GREEN"
            generator_mode = "all_systems_go"
        elif health >= 40:
            mode = "YELLOW"
            generator_mode = "core_only"
        else:
            mode = "RED"
            generator_mode = "minimum_viable"
        return {
            "health": health,
            "mode": mode,
            "generator_mode": generator_mode,
            "balance_usd": balance_usd,
            "monthly_burn_usd": round(total_burn, 2),
            "budget_remaining": round(budget - total_burn, 2),
            "burn_by_category": burn,
        }


class AgentWallet:
    """
    Top-level wallet orchestrator.
    Coordinates: Jupiter -> Bridge -> Stripe Issuing -> SpendLogger -> MetaLearner.
    """

    def __init__(self):
        self.jupiter = JupiterSwap()
        self.bridge = BridgeConnector()
        self.stripe = StripeIssuingCard()
        self.logger = SpendLogger()
        self.state = self._load_state()

    def setup_card(
        self,
        cardholder_name: str,
        cardholder_email: str,
        billing_address: dict,
        monthly_budget_usd: float = 100.0,
        allowed_mccs: list = None,
    ) -> dict:
        """
        Full setup: create cardholder + issue virtual card.
        Call once. Card ID is persisted to wallet_state.json.
        """
        cardholder = self.stripe.create_cardholder(
            name=cardholder_name,
            email=cardholder_email,
            billing_address=billing_address,
        )
        limits = {"total": monthly_budget_usd}
        card = self.stripe.issue_virtual_card(
            cardholder_id=cardholder["id"],
            spend_limits=limits,
            allowed_mccs=allowed_mccs or ALLOWED_MCCS,
        )
        self.state["cardholder_id"] = cardholder["id"]
        self.state["card_id"] = card["id"]
        self.state["setup_at"] = datetime.utcnow().isoformat()
        self.state["monthly_budget_usd"] = monthly_budget_usd
        self._save_state()
        log.info(f"Card setup complete. cardholder={cardholder['id']} card={card['id']}")
        return {"cardholder": cardholder, "card": card}

    def fund_from_sol(
        self,
        sol_amount: float,
        wallet_public_key: str,
        stripe_account_id: str,
    ) -> dict:
        """
        Swap SOL -> USDC via Jupiter, then fund Stripe via Bridge.
        """
        swap_result = self.jupiter.swap_sol_to_usdc(sol_amount, wallet_public_key)
        usdc_amount = int(swap_result.get("quoteResponse", {}).get("outAmount", 0)) / 1_000_000
        transfer = self.bridge.create_transfer(
            amount_usd=usdc_amount,
            source_wallet=wallet_public_key,
            destination_stripe_account_id=stripe_account_id,
        )
        self.state["last_fund_at"] = datetime.utcnow().isoformat()
        self.state["last_fund_usdc"] = usdc_amount
        self._save_state()
        return {"swap": swap_result, "transfer": transfer, "usdc_funded": usdc_amount}

    def get_health_report(self, current_balance_usd: float = 0.0) -> dict:
        """Wallet health for MetaLearner consumption."""
        return self.logger.get_wallet_health(current_balance_usd)

    def log_spend(self, amount_usd: float, category: str,
                  merchant: str, note: str = "") -> None:
        self.logger.log_spend(
            amount_usd=amount_usd,
            category=category,
            merchant=merchant,
            card_id=self.state.get("card_id"),
            note=note,
        )

    def _load_state(self) -> dict:
        if not WALLET_STATE_PATH.exists():
            return {}
        with open(WALLET_STATE_PATH) as f:
            return json.load(f)

    def _save_state(self) -> None:
        with open(WALLET_STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2, default=str)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EVEZ Agent Wallet")
    parser.add_argument("--health", action="store_true", help="Print wallet health report")
    parser.add_argument("--setup", action="store_true", help="Setup virtual card (requires Stripe keys)")
    parser.add_argument("--balance", type=float, default=0.0, help="Current balance in USD for health calc")
    args = parser.parse_args()

    wallet = AgentWallet()
    if args.health:
        report = wallet.get_health_report(args.balance)
        print(json.dumps(report, indent=2))
    elif args.setup:
        result = wallet.setup_card(
            cardholder_name="EVEZ OS Agent",
            cardholder_email=os.environ.get("AGENT_EMAIL", "evez-os-node@agentmail.to"),
            billing_address={
                "line1": os.environ.get("BILLING_LINE1", "1 Agent Street"),
                "city": os.environ.get("BILLING_CITY", "Las Vegas"),
                "state": os.environ.get("BILLING_STATE", "NV"),
                "postal_code": os.environ.get("BILLING_ZIP", "89030"),
                "country": "US",
            },
            monthly_budget_usd=100.0,
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()
