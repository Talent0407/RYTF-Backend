import datetime
import json
import logging
import re
from typing import Optional

import pytz
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import Group, User
from ens import ENS
from siwe.siwe import (  # ExpiredMessage,; InvalidSignature,; MalformedSession,; ValidationError,
    SiweMessage,
)
from siwe_auth.custom_groups.group_manager import GroupManager
from siwe_auth.models import Nonce, Wallet
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware

from ryft.core.models import DiscordUser


def _nonce_is_valid(nonce: str) -> bool:
    """
    Check if given nonce exists and has not yet expired.
    :param nonce: The nonce string to validate.
    :return: True if valid else False.
    """
    n = Nonce.objects.get(value=nonce)
    is_valid = False
    if n is not None and n.expiration > datetime.datetime.now(tz=pytz.UTC):
        is_valid = True
    n.delete()
    return is_valid


class SiweBackend(BaseBackend):
    """
    Authenticate an Ethereum address as per Sign-In with Ethereum (EIP-4361).
    """

    def authenticate(
        self, request, signature: str = None, siwe_message: SiweMessage = None
    ):
        body = json.loads(request.body)

        # TODO massive bug here. Signing a message from the mobile app does not produce the same hash
        #  compared to when done on the web app directly with metamask

        if siwe_message is None:
            siwe_message = SiweMessage(
                message={
                    re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower(): v
                    for k, v in body["message"].items()
                }
            )
            # signature = body["signature"]

        # # Validate signature
        w3 = Web3(HTTPProvider(settings.PROVIDER))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        #
        # try:
        #     siwe_message.validate(signature=signature, provider=w3)
        # except ValidationError:
        #     logging.info("Authentication attempt rejected due to invalid message.")
        #     return None
        # except ExpiredMessage:
        #     logging.info("Authentication attempt rejected due to expired message.")
        #     return None
        # except MalformedSession as e:
        #     logging.info(
        #         f"Authentication attempt rejected due to missing fields: {', '.join(e.missing_fields)}"
        #     )
        #     return None
        # except InvalidSignature:
        #     logging.info("Authentication attempt rejected due to invalid signature.")
        #     return None

        # Validate nonce
        if not _nonce_is_valid(siwe_message.nonce):
            return None

        # Pull ENS data
        if getattr(settings, "CREATE_ENS_PROFILE_ON_AUTHN", True):
            ens_profile = ENSProfile(ethereum_address=siwe_message.address, w3=w3)
        else:
            ens_profile = ENSProfile.__new__(
                ENSProfile
            )  # blank ENSProfile, skipping __init__ constructor

        # Message and nonce has been validated. Authentication complete. Continue with authorization/other.
        now = datetime.datetime.now(tz=pytz.UTC)
        try:
            wallet = Wallet.objects.get(ethereum_address=siwe_message.address)
            wallet.last_login = now
            wallet.ens_name = ens_profile.name
            wallet.save()
            logging.debug(f"Found wallet for address {siwe_message.address}")
        except Wallet.DoesNotExist:
            wallet = Wallet(
                ethereum_address=Web3.toChecksumAddress(siwe_message.address),
                ens_name=ens_profile.name,
                ens_avatar=ens_profile.avatar,
                last_login=now,
                password=None,
                created=now,
            )
            wallet.set_unusable_password()
            wallet.save()
            logging.debug(
                f"Could not find wallet for address {siwe_message.address}. Creating new wallet object."
            )

        # Group settings
        if getattr(settings, "CREATE_GROUPS_ON_AUTHN", False):
            for custom_group in settings.CUSTOM_GROUPS:
                group, created = Group.objects.get_or_create(name=custom_group[0])
                if created:
                    logging.info(f"Created group '{custom_group[0]}'.")
                group_manager: GroupManager = custom_group[1]
                if group_manager.is_member(
                    wallet=wallet,
                    provider=HTTPProvider(settings.PROVIDER),
                ):
                    logging.info(
                        f"Adding wallet '{wallet.ethereum_address}' to group '{custom_group[0]}'."
                    )
                    wallet.groups.add(group)

        return wallet

    def get_user(self, ethereum_address: str) -> Optional[Wallet]:
        """
        Get Wallet by ethereum address if exists.
        :param ethereum_address: Ethereum address of user.
        :return: Wallet object if exists or None
        """
        try:
            return Wallet.objects.get(pk=ethereum_address)
        except User.DoesNotExist:
            return None


class ENSProfile:
    """
    Container for ENS profile information including but not limited to primary name and avatar.
    """

    name: str = None
    avatar: str = None

    def __init__(self, ethereum_address: str, w3: Web3):
        # Temporary until https://github.com/ethereum/web3.py/pull/2286 is merged
        self.name = ENS.fromWeb3(w3).name(address=ethereum_address)
        ENS.fromWeb3(w3).resolver(normal_name=self.name)
        # if resolver:
        #     self.avatar = resolver.caller.text(normal_name_to_hash(self.name), 'avatar')


class DiscordAuthenticationBackend(BaseBackend):
    def authenticate(self, request, oauth_data: dict):
        # Usually this does a form of password validation but for OAuth2 we don't need
        # to do anything here - just fetch the user

        try:
            discord_user = DiscordUser.objects.get(id=oauth_data["id"])
            self.set_auth_tokens(discord_user, oauth_data)
            self.set_beta_user_status(discord_user, oauth_data)
            return discord_user.user
        except DiscordUser.DoesNotExist:
            if not request.user.is_authenticated:
                return None
            discord_user = DiscordUser.objects.create_new_discord_user(
                oauth_data, request.user
            )
            self.set_beta_user_status(discord_user, oauth_data)
            return discord_user.user

    def get_user(self, ethereum_address: str) -> Optional[Wallet]:
        """
        Get Wallet by ethereum address if exists.
        :param ethereum_address: Ethereum address of user.
        :return: Wallet object if exists or None
        """
        try:
            return Wallet.objects.get(pk=ethereum_address)
        except Wallet.DoesNotExist:
            return None

    def set_beta_user_status(self, discord_user: DiscordUser, oauth_data):
        wallet = discord_user.user.wallet
        wallet.is_beta = oauth_data["is_beta_user"]
        wallet.save()
        return wallet

    def set_auth_tokens(self, discord_user: DiscordUser, oauth_data):
        discord_user.refresh_token = oauth_data["refresh_token"]
        discord_user.access_token = oauth_data["access_token"]
        discord_user.save()
