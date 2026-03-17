from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [

    # ================= AUTH =================
    path("", views.admin_login, name="admin_login"),

    # ================= DASHBOARD =================
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # ================= CATEGORIES =================
    path("categories/", views.categories, name="categories"),
    path("categories/edit/<int:id>/", views.edit_category, name="edit_category"),
    path("categories/delete/<int:id>/", views.delete_category, name="delete_category"),

    # ================= ATTRIBUTES =================
    path("attribute/edit/<int:id>/", views.edit_attribute, name="edit_attribute"),
    path("attribute/delete/<int:id>/", views.delete_attribute, name="delete_attribute"),
    path("category-attributes/", views.category_attributes_page, name="category_attributes"),

    # ================= PRODUCTS =================
    path("products/", views.admin_products, name="admin_products"),
    path("products/<int:id>/", views.product_detail, name="admin_product_detail"),
    path("products/edit/<int:id>/", views.edit_product, name="admin_edit_product"),
    path("products/delete/<int:id>/", views.delete_product, name="delete_product"),
    path("products/toggle/<int:id>/", views.toggle_product_status, name="toggle_product_status"),
    path("products/approve/<int:id>/", views.approve_product, name="approve_product"),

    # ================= ORDERS =================
    path("orders/", views.orders, name="orders"),

    # ================= USERS =================
    path("users/", views.users, name="users"),

    # ================= VENDORS =================
    path("vendors/", views.vendor_list, name="vendor_list"),
    path("vendors/<int:vendor_id>/chat/", views.vendor_chat, name="vendor_chat"),

    # ================= REVIEWS =================
    path("reviews/", views.admin_reviews, name="admin_reviews"),
    path("reviews/approve/<int:review_id>/", views.approve_review, name="approve_review"),
    path("reviews/reject/<int:review_id>/", views.reject_review, name="reject_review"),
    path("reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),

    # ================= BUNDLES =================
    path("bundles/", views.admin_bundles, name="admin_bundles"),
    path("bundles/create/", views.create_bundle, name="create_bundle"),
    path("bundles/edit/<int:bundle_id>/", views.edit_bundle, name="edit_bundle"),
    path("bundles/delete/<int:bundle_id>/", views.delete_bundle, name="delete_bundle"),

    # ================= SALES =================
    path("sales/", views.admin_sales, name="admin_sales"),
    path("sales/create/", views.create_sale, name="create_sale"),
    path("sales/edit/<int:sale_id>/", views.edit_sale, name="edit_sale"),
    path("sales/delete/<int:sale_id>/", views.delete_sale, name="delete_sale"),
    path("sales/<int:sale_id>/ads/", views.admin_sale_ads, name="admin_sale_ads"),
    path("sales/ads/approve/<int:ad_id>/", views.approve_sale_ad, name="approve_sale_ad"),
    path("sales/ads/reject/<int:ad_id>/", views.reject_sale_ad, name="reject_sale_ad"),
    path("sales/end/<int:sale_id>/", views.end_sale, name="end_sale"),
]