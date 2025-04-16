from django.urls import path
from .views import *

urlpatterns = [
    path('login',login_view, name='login'),
    path('',home, name='home'),
    path('logout/',logout_view, name='logout'),
    path('upload/', upload_excel, name='upload_excel'),
    path('upload/success/',upload_success, name='upload_success'),
    path('auth/password/modify/',modifyPassword, name='modifyPassword'),
]