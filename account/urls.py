from django.urls import path

from . import views

urlpatterns = [
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_create, name="staff_create"),
    path("staff/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("staff/<int:pk>/edit/", views.staff_update, name="staff_update"),
    path("staff/<int:pk>/toggle-active/", views.staff_toggle_active, name="staff_toggle_active"),
    path("profile/", views.my_profile, name="my_profile"),
    path("profile/edit/", views.my_profile_update, name="my_profile_update"),
    path("password/", views.password_change, name="password_change"),
]
