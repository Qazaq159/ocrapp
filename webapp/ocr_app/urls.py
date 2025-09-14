from django.urls import path
from ocr_app import views


urlpatterns = [
    path('', views.index, name='index'),
    path('documents/', views.document_list, name='document_list'),
    path('documents/<int:document_id>/', views.document_detail, name='document_detail'),
]
