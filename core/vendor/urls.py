from django.urls import path
from . import views

urlpatterns = [

    path("login/", views.vendor_login, name="vendor_login"),
    path("dashboard/", views.dashboard, name="vendor_dashboard"),

    path("products/", views.vendor_products, name="vendor_products"),
    path("add/", views.add_product, name="vendor_add"),
    
    # New professional product management
    # path("add-v2/", views_v2.add_product_v2, name="vendor_add_v2"),
    # path("edit-v2/<int:product_id>/", views_v2.add_product_v2, name="vendor_edit_v2"),

    path("edit/<int:id>/", views.edit_product, name="vendor_edit"),
    path("view/<int:id>/", views.vendor_view_product, name="vendor_view_product"),
    path("delete/<int:id>/", views.vendor_delete, name="vendor_delete"),

    path("profile/", views.vendor_profile, name="vendor_profile"),

    path("orders/", views.vendor_orders, name="vendor_orders"),
    path("order/accept/<int:id>/", views.accept_order, name="accept_order"),
    path("order/reject/<int:id>/", views.reject_order, name="reject_order"),
    path("order/update-status/<int:id>/", views.update_order_status, name="update_order_status"),
    path("add-variants/<int:product_id>/", views.add_variants, name="vendor_add_variants"),
    path("variant/delete/<int:variant_id>/", views.delete_variant, name="vendor_delete_variant"),
    path("variant/edit/<int:variant_id>/",   views.edit_variant,   name="vendor_edit_variant"),
    path("get-category-attributes/", views.get_category_attributes, name="get_category_attributes"),
    path("inbox/", views.vendor_inbox, name="vendor_inbox"),
    path("analytics/", views.vendor_analytics, name="vendor_analytics"),
    path("reviews/", views.vendor_reviews, name="vendor_reviews"),
    path("reviews/action/", views.vendor_review_action, name="vendor_review_action"),
    path("sales/", views.vendor_sales, name="vendor_sales"),
    path("sales/<int:sale_id>/submit/", views.vendor_submit_ad, name="vendor_submit_ad"),
]
