from django.urls import path

from . import views

urlpatterns = [
    path("clients/", views.client_list, name="client_list"),
    path("sites/", views.site_list, name="site_list"),
    path("proformas/", views.proforma_list, name="proforma_list"),
    path("proformas/<int:pk>/", views.proforma_detail, name="proforma_detail"),
    path("proformas/<int:pk>/quote/", views.proforma_quote, name="proforma_quote"),
    path("proformas/<int:pk>/pdf/", views.proforma_pdf, name="proforma_pdf"),
]
