from django.contrib.auth.views import LogoutView
from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("logout/", views.logout_view, name="logout"),
    path('apply/<int:project_id>/', views.apply_project, name='apply_project'),
    path('manage-request/<int:request_id>/<str:action>/', views.manage_request, name='manage_request'),
    path('create-project/', views.create_project, name='create_project'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete_project'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('update-password/', views.update_password, name='update_password'),
]
