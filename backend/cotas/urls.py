from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'modalidades', views.ModalidadeViewSet, basename='modalidade')
router.register(r'inscricoes', views.InscricaoCotaViewSet, basename='inscricao')

urlpatterns = [
    path('', include(router.urls)),
]
