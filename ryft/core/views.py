import json
import secrets
import urllib.parse
from datetime import datetime, timedelta

import pytz
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from siwe.siwe import SiweMessage
from siwe_auth.models import Nonce

from ryft.core.authentication import CsrfExemptSessionAuthentication
from ryft.core.models import DiscordUser, Wallet
from ryft.core.portfolio.tasks import run_new_wallet_tasks


@ratelimit(key="ip", rate="5/m")
@require_http_methods(["POST"])
@csrf_exempt
def logout(request):
    auth_logout(request)
    return JsonResponse({"success": True, "message": "Successful logout."})


@ensure_csrf_cookie
def index(request):
    return render(request, "core/app/index.html")


@ratelimit(key="ip", rate="5/m")
@require_http_methods(["POST"])
@csrf_exempt
def login(request):
    wallet_user = authenticate(request)
    if wallet_user is not None:
        if wallet_user.is_active:
            auth_login(request, wallet_user)
            wallet, created = Wallet.objects.get_or_create(
                user=wallet_user,
                wallet_address=wallet_user.ethereum_address.lower(),
                active=True,
            )
            data = {
                "processed": wallet.processed,
                "has_access": wallet.has_access,
                "success": True,
                "message": "Successful login.",
            }
            # TODO test this
            if created:
                transaction.on_commit(
                    lambda: run_new_wallet_tasks(wallet.wallet_address)
                )
            return JsonResponse(data)
        else:
            return JsonResponse(
                {"success": False, "message": "Wallet disabled."}, status=401
            )
    return JsonResponse({"success": False, "message": "Invalid login."}, status=403)


def create_nonce() -> Nonce:
    now = datetime.now(tz=pytz.UTC)

    _scrub_nonce()
    n = Nonce(value=secrets.token_hex(12), expiration=now + timedelta(hours=12))
    n.save()

    return n


@ratelimit(key="ip", rate="5/m")
@require_http_methods(["GET"])
def nonce(request):
    n = create_nonce()

    return JsonResponse({"nonce": n.value})


def _scrub_nonce():
    # Delete all expired nonce's
    Nonce.objects.filter(expiration__lte=datetime.now(tz=pytz.UTC)).delete()


@ratelimit(key="ip", rate="5/m")
@require_http_methods(["POST"])
@csrf_exempt
def siwe_message(request):
    body_unicode = request.body.decode("utf-8")
    body = json.loads(body_unicode)

    address = body["address"]
    nonce = create_nonce()
    issued_at = datetime.now().isoformat()

    siwe_message = SiweMessage(
        message={
            "domain": "api.ryftpass.io",
            "address": address,
            "statement": "Ryft Pass",
            "uri": "https://api.ryftpass.io",
            "version": "1",
            "chain_id": 1,
            "nonce": nonce.value,
            "issued_at": issued_at,
        }
    )

    message = siwe_message.prepare_message()

    return JsonResponse(
        {"message": message, "issued_at": issued_at, "nonce": nonce.value}, status=201
    )


@login_required(login_url="/api/oauth2/login/")
def get_authenticated_user(request):
    user = request.user
    discord_user = DiscordUser.objects.get(user=user)
    if not discord_user.refresh_token:
        return JsonResponse(
            {"message": "Please reconnect your discord account"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return JsonResponse(
        {
            "id": discord_user.id,
            "username": discord_user.username,
            "discord_tag": discord_user.discord_tag,
            "avatar": discord_user.avatar,
            "public_flags": discord_user.public_flags,
            "flags": discord_user.flags,
            "locale": discord_user.locale,
            "mfa_enabled": discord_user.mfa_enabled,
        }
    )


def discord_login(request):
    url = "https://discord.com/api/oauth2/authorize?"
    redirect_url = "https://api.ryftpass.io"
    if settings.DEBUG:
        redirect_url = "http://127.0.0.1:8000"
    params = {
        "client_id": settings.DISCORD_APP_CLIENT_ID,
        "redirect_uri": redirect_url + reverse("discord_login_redirect"),
        "response_type": "code",
        "scope": " ".join(["identify", "guilds", "guilds.members.read"]),
    }
    return redirect(url + urllib.parse.urlencode(params))


def discord_callback(request):
    # This returns a template with a button so the user can be redirected back to the app
    code = request.GET.get("code")
    context = {"ryft_app_url": f"ryft://callback?code={code}"}
    return render(request, "discord/app_redirect.html", context)


class DiscordWebConnectView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        # Attaches request user to discord profile
        code = request.data.get("code")
        if not code:
            return Response({"error": "Code not provided"}, status=400)

        redirect_uri = "https://connect.ryftpass.io/callback"
        if settings.DEBUG:
            redirect_uri = "http://127.0.0.1:3000/callback"

        user_data = exchange_code(code, redirect_uri=redirect_uri)
        user = authenticate(request, oauth_data=user_data)
        if not user:
            return Response({"success": False}, status=400)

        # setting display name to be the Discord username by default
        wallet_user = Wallet.objects.get(user=request.user)
        if not wallet_user.display_name:
            wallet_user.display_name = user_data["username"]
            wallet_user.save()

        return Response({"success": True})


discord_connect_view = DiscordWebConnectView.as_view()


class DiscordLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, *args, **kwargs):
        # User login with discord profile
        code = request.data.get("code")
        if not code:
            return Response({"error": "Code not provided"}, status=400)

        redirect_uri = "https://api.ryftpass.io" + reverse("discord_login_redirect")
        if settings.DEBUG:
            redirect_uri = "http://127.0.0.1:8000" + reverse("discord_login_redirect")

        user_data = exchange_code(code, redirect_uri=redirect_uri)
        user = authenticate(request, oauth_data=user_data)
        if not user:
            return Response({"success": False}, status=400)

        auth_login(
            request, user, backend="ryft.core.backend.DiscordAuthenticationBackend"
        )
        return Response({"success": True, "wallet_address": user.wallet.wallet_address})


discord_login_view = DiscordLoginView.as_view()


def exchange_code(code: str, redirect_uri: str):
    data = {
        "client_id": settings.DISCORD_APP_CLIENT_ID,
        "client_secret": settings.DISCORD_APP_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": " ".join(["identify", "guilds", "guilds.members.read"]),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(
        "https://discord.com/api/oauth2/token", data=data, headers=headers
    )
    credentials = response.json()
    access_token = credentials["access_token"]
    auth_headers = {"Authorization": "Bearer %s" % access_token}
    user_response = requests.get(
        "https://discord.com/api/users/@me", headers=auth_headers
    )
    user = user_response.json()

    ryft_guild_id = settings.RYFT_DISCORD_SERVER_ID
    ryft_beta_user_role_id = settings.RYFT_DISCORD_BETA_USER_ROLE_ID

    # Fetch user role in server
    try:
        server_role_response = requests.get(
            f"https://discord.com/api/users/@me/guilds/{ryft_guild_id}/member",
            headers=auth_headers,
        )
        server_roles = server_role_response.json()
        server_role_ids = server_roles["roles"]
    except KeyError:
        # User is not in this guild
        server_role_ids = []

    user["is_beta_user"] = ryft_beta_user_role_id in server_role_ids
    user["access_token"] = credentials["access_token"]
    user["refresh_token"] = credentials["refresh_token"]

    return user
