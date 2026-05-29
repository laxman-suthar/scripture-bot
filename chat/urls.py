from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_ui, name='chat-ui'),
    path('api/chat/', views.chat_api, name='chat-api'),
]
