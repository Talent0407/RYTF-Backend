import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings
from requests import HTTPError

from ryft.core.models import DiscordUser

logger = logging.getLogger(__name__)

DISCORD_API_ENDPOINT = "https://discord.com/api"


def is_valid_signature_for_string_body(
    body: bytes, signature: str, signing_key: str
) -> bool:
    digest = hmac.new(
        bytes(signing_key, "utf-8"), msg=body, digestmod=hashlib.sha256
    ).hexdigest()

    return signature == digest


def refresh_access_token(user_id):
    instance = DiscordUser.objects.get(user_id)

    try:

        data = {
            "client_id": settings.DISCORD_APP_CLIENT_ID,
            "client_secret": settings.DISCORD_APP_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": instance.refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        r = requests.post(
            f"{DISCORD_API_ENDPOINT}/oauth2/token", data=data, headers=headers
        )
        r.raise_for_status()
        instance.access_token = r.json()["access_token"]
        instance.save()
        return {"Authorization": "Bearer %s" % instance.access_token}
    except HTTPError as e:
        if e.response.status == 401 or e.response.status == 403:
            logger.warning("Expired Refresh token for Discord ID: " + instance.id)
            instance.refresh_token = None
            instance.access_token = None
            instance.save()
        logger.error(e)


def discord_request(method, request_url, data, headers, user_id):
    try:
        if method == "POST":
            r = requests.post(request_url, data=data, headers=headers)
        else:
            r = requests.get(request_url, data=data, headers=headers)
        r.raise_for_status()
        return r.json()
    except HTTPError as e:
        if e.response.status == 401 or e.response.status == 403:
            refreshed_auth_headers = refresh_access_token(user_id)
            if not refreshed_auth_headers:
                return {"refresh_token": "expired"}
            return discord_request(
                method, request_url, data, refreshed_auth_headers, user_id
            )
        elif e.response.status == 429:
            response_json = e.response.json()
            # wait for retry_after seconds
            time.sleep(response_json["retry_after"])
            # retry request
            return discord_request(method, request_url, data, headers, user_id)
        else:
            logger.error(e)


def get_user_discord_roles(request):
    try:
        discord_user = DiscordUser.objects.get(user=request.user)
    except DiscordUser.DoesNotExist:
        return None
    ryft_guild_id = settings.RYFT_DISCORD_SERVER_ID
    auth_headers = {"Authorization": "Bearer %s" % discord_user.access_token}
    # fetch user roles
    guild_user = discord_request(
        "GET",
        f"{DISCORD_API_ENDPOINT}/users/@me/guilds/{ryft_guild_id}/member",
        {},
        auth_headers,
        discord_user.id,
    )
    return guild_user
