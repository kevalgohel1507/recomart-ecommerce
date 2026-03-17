from .models import Category
from django.db.models import Prefetch


def nav_categories(request):
    # Prefetch 3 levels: root → children → grandchildren
    # This covers: nav tab → bold column headers → normal sub-links
    grandchildren_qs = Category.objects.all()
    children_qs = Category.objects.prefetch_related(
        Prefetch("children", queryset=grandchildren_qs)
    )
    categories = Category.objects.filter(parent__isnull=True).prefetch_related(
        Prefetch("children", queryset=children_qs)
    )
    return {"nav_categories": categories}
