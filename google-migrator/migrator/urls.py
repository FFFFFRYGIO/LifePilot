from django.urls import path

from . import views

app_name = "migrator"

urlpatterns = [
    path("", views.connections, name="connections"),
    path("connections/lists/", views.lists_fragment, name="lists_fragment"),
    path("oauth/<str:provider>/start/", views.oauth_start, name="oauth_start"),
    path("oauth/<str:provider>/callback", views.oauth_callback, name="oauth_callback"),
    path("oauth/<str:provider>/disconnect/", views.disconnect, name="disconnect"),
]
