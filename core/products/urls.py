from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:slug>/", views.category_page, name="category_page"),
    path("product/<int:id>/", views.product_detail, name="product_detail"),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("search-index/", views.search_index, name="search_index"),
    path("track/", views.track_interaction, name="track_interaction"),
    path("vendor/add/", views.vendor_add_product, name="vendor_add_product"),
    path("vendor/color/<int:product_id>/", views.vendor_add_color, name="vendor_add_color"),
    path("vendor/sizes/<int:product_id>/<str:color>/", views.vendor_add_sizes, name="vendor_add_sizes"),
    path("vendor/save/<int:product_id>/<str:color>/", views.save_variants, name="save_variants"),
    path("variant-price/", views.variant_price, name="variant_price"),
    path("chatbot/", views.chatbot_api, name="chatbot_api"),
    path("product/<int:product_id>/review/submit/", views.submit_review, name="submit_review"),
    path("product/<int:product_id>/review/load/", views.load_reviews, name="load_reviews"),
]
