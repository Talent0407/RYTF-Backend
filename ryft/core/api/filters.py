from django_filters import rest_framework as filters

from ryft.core.models import Collection, TrackedWallet, Transaction


class CollectionFilter(filters.FilterSet):
    floor_price = filters.NumberFilter()
    floor_price__gt = filters.NumberFilter(
        field_name="collectionmetrics__current_floor_price", lookup_expr="gt"
    )
    floor_price__lt = filters.NumberFilter(
        field_name="collectionmetrics__current_floor_price", lookup_expr="lt"
    )

    sales = filters.NumberFilter()
    sales__gt = filters.NumberFilter(
        field_name="collectionmetrics__average_sales_24hr", lookup_expr="gt"
    )
    sales__lt = filters.NumberFilter(
        field_name="collectionmetrics__average_sales_24hr", lookup_expr="lt"
    )

    class Meta:
        model = Collection
        fields = ["floor_price", "sales"]


class CollectionTransfersFilter(filters.FilterSet):
    transaction_date = filters.DateTimeFilter()
    transaction_date__gt = filters.DateTimeFilter(
        field_name="transaction_date", lookup_expr="gt"
    )
    transaction_date__lt = filters.DateTimeFilter(
        field_name="transaction_date", lookup_expr="lt"
    )

    class Meta:
        model = Transaction
        fields = ["transaction_date"]


class TrackedWalletFilter(filters.FilterSet):
    wallet_address = filters.CharFilter(
        field_name="wallet__wallet_address", lookup_expr="icontains"
    )

    class Meta:
        model = TrackedWallet
        fields = ["wallet_address"]
