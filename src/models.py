import asyncio
import math
import os
import secrets

import lnurl
import requests

from .handler import PhoenixdHandler
from .lnurl_handler import FundSource, LnurlHandler, logger, parse_username

API_KEY = os.getenv("NODE_API_KEY")
NODE_URL = os.getenv("NODE_BASE_URL")
LN_ADDRESS_DOMAIN = os.getenv("LN_ADDRESS_DOMAIN")
LN_USERNAME = os.getenv("LN_USERNAME", "phoenixd")


def new_phoenix_client():
    return PhoenixdHandler(base_url=NODE_URL, api_key=API_KEY)


def run_async(coroutine):
    try:
        return asyncio.run(coroutine)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)


class AppFundingSource(FundSource):
    async def get_owner(self, owner: str):
        return {"owner": owner}

    async def deposit_funds(self, owner: str, amount: int) -> str:
        if owner == LN_USERNAME:
            client = new_phoenix_client()
            result = client.create_invoice(
                {"amount_sat": amount, "description": "Deposit"}
            )
            return result["serialized"]
        return await super().deposit_funds(owner, amount)


class AppLnurlHandler(LnurlHandler):
    async def lnurl_pay_request_callback_lud06(
        self,
        username: str,
        amount: int,
        tag="message",
        message=lambda x: f"Thanks for zapping {x}",
    ) -> lnurl.LnurlPayActionResponse:
        """path="/lnurlp/{username}/callback","""
        await self.get_address(parse_username(username))
        if not self.lnurl_address:
            return None
        username = self.username

        # TODO check compatibility of conversion to sats, some wallets
        # may not like the invoice amount not matching?
        amount_sat = math.ceil(amount / 1000)
        logger.info(
            "LUD-06 payRequestCallback for username='{username}' sat={amount_sat} (mSat={amount})".format(
                username=username,
                amount_sat=amount_sat,
                amount=amount,
            )
        )

        if amount_sat < self.min_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-low amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        if amount_sat > self.max_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-high amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        invoice = await self.service.deposit_funds(username, amount_sat)
        if not invoice:
            logger.warning("Failed to generate lightning invoice")
            return None
        payload = dict(
            pr=invoice,
            routes=[],
        )
        return lnurl.LnurlPayActionResponse.parse_obj(payload)

    def generate_invoice(self, username: str, amount: int):
        result = run_async(
            self.lnurl_pay_request_callback_lud06(
                username,
                amount,
                tag="payRequest",
                message=lambda x: f"Payment to ln address for {x}",
            )
        )
        return result

    def get_ln_details(self, username: str):
        result = run_async(self.lnurl_pay_request_lud16(username))
        return result

    def get_user(self, username: str):
        if username == "local":
            return True
        return username == LN_USERNAME

    def to_url(self, identifier, is_dev=False):
        parts = identifier.split("@")
        if len(parts) != 2:
            raise ValueError(f"Invalid lightning address {identifier}")

        domain = parts[1]
        username = parts[0]
        protocol = "http" if is_dev else "https"
        keysend_url = f"{protocol}://{domain}/.well-known/keysend/{username}"
        lnurlp_url = f"{protocol}://{domain}/.well-known/lnurlp/{username}"
        nostr_url = f"{protocol}://{domain}/.well-known/nostr.json?name={username}"
        return lnurlp_url, keysend_url, nostr_url

    def get_json(self, url):
        response = requests.get(url)
        if response.status_code >= 300:
            raise Exception(f"Request failed with status {response.status_code}")
        return response.json()

    def lnurl_address_encoded(self, url: str) -> lnurl.Lnurl:
        return lnurl.encode(url)


handler = AppLnurlHandler(
    domain=LN_ADDRESS_DOMAIN,
    service=AppFundingSource(),
    min_sats_receivable=0.00000001 * 100_000_000,
    max_sats_receivable=0.01 * 100_000_000,
)
