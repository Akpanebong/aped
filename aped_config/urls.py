from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from account.forms import IdentifierAuthenticationForm
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='account/login.html', authentication_form=IdentifierAuthenticationForm), name='login'),
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(template_name='account/password_reset_form.html', email_template_name='registration/password_reset_email.txt', subject_template_name='registration/password_reset_subject.txt'), name='password_reset'),
    path('accounts/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='account/password_reset_done.html'), name='password_reset_done'),
    path('accounts/password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='account/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='account/password_reset_complete.html'), name='password_reset_complete'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('account.urls')),
    path('', include('core.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('vsla/', include('vsla_app.vsla.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
