from django.core.management.base import BaseCommand
from products.models import UserProductInteraction
import pandas as pd

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        data = UserProductInteraction.objects.all().values(
            "user_id",
            "product_id",
            "interaction_type",
            "created_at"
        )

        df = pd.DataFrame(list(data))
        df.to_csv("training_data.csv", index=False)

        print("✅ CSV exported successfully!")