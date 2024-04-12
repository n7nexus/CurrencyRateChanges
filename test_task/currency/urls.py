from django.urls import path
from .views import CurrencyChangesView

urlpatterns = [
    path("", CurrencyChangesView.as_view(), name="home"),
]