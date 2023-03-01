from rest_framework import permissions

from ryft.core.models import DiscordUser, Wallet


class IsWalletOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of a wallet to view it.
    """

    def has_object_permission(self, request, view, obj: Wallet):
        return obj.user == request.user


class IsMember(permissions.BasePermission):
    """
    View-level permission to only allow members access to the app
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # user: User = request.user
        # user_wallet = user.wallet
        # return user_wallet.is_member or user_wallet.is_beta
        return True


class IsBetaUser(permissions.BasePermission):
    """
    View-level permission to only allow members with beta acccess to the view
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        wallet = Wallet.objects.get(user=request.user)
        if not wallet:
            return False
        return wallet.is_beta


class IsValidDiscordUser(permissions.BasePermission):
    """
    View-level permission to only allow members with connected discord account
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        discord = DiscordUser.objects.get(user=request.user)
        if not discord:
            return False
        return len(discord.refresh_token) != 0
