import time

from celery.result import AsyncResult
from django.core.management.base import BaseCommand

from ryft.core.models import Collection
from ryft.core.tasks import calculate_collection_rarity_task


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Start again at 1225
        qs = Collection.objects.filter(id__gt=29, id__lte=50).order_by("id")
        for collection in qs:
            print(f"Performing tasks on contract: {collection.contract_address}")
            result = calculate_collection_rarity_task(collection.contract_address)
            res = AsyncResult(result.task_id)
            while not res.successful():
                time.sleep(10)
