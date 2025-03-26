"""
Definition of urls for _1_Ollama_App.
"""

from datetime import datetime
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from app import forms, views
from ollama_backend.views import ollama_chat_detail, ollama_chat_update_title, ollama_chats, ollama_check, ollama_post, ollama_post_existing, ollama_presets, ollama_response_test


urlpatterns = [
    path('', views.home, name='home'),
    path('chat/<str:id_chat>/', views.detailChat, name='detailChat'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('login/',
         LoginView.as_view
         (
             template_name='app/login.html',
             authentication_form=forms.BootstrapAuthenticationForm,
             extra_context=
             {
                 'title': 'Log in',
                 'year' : datetime.now().year,
             }
         ),
         name='login'),
    path('register/', views.register, name='register'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('admin/', admin.site.urls),
    # Lalu, implementasikan fungsi ollama_response_test ke dalam route baru dengan endpoint ollama/test/ menggunakan method POST
    path('ollama/test/', ollama_response_test, name='ollama_response_test'),
    # Implementasikan fungsi ollama_check ke dalam route baru dengan endpoint ollama/check/ menggunakan method GET
    path('ollama/check/', ollama_check, name='ollama_check'),
    path('ollama/presets/', ollama_presets, name='ollama_presets'),
    # Implementasikan fungsi ollama_post ke dalam route baru dengan endpoint ollama/post/ menggunakan method POST
    path('ollama/post/', ollama_post, name='ollama_post'),
    path('ollama/post/<str:id_chat>/', ollama_post_existing, name='ollama_post_existing'),
    # Implementasikan fungsi ollama_chats ke dalam route baru dengan endpoint ollama/chats/ menggunakan method GET
    path('ollama/chats/', ollama_chats, name='ollama_chats'),
    # Implementasikan fungsi ollama_chat_detail ke dalam route baru dengan endpoint ollama/chat/{id_chat} menggunakan method GET
    path('ollama/chat/<str:id_chat>/', ollama_chat_detail, name='ollama_chat_detail'),
    # Implementasikan fungsi ollama_chat_update_title ke dalam route baru dengan endpoint ollama/chat/{id_chat}/title menggunakan method PUT
    path('ollama/chat/<str:id_chat>/title', ollama_chat_update_title, name='ollama_chat_update_title'),
]

handler404 = 'app.views.not_found'