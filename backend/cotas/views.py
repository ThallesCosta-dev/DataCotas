from rest_framework import viewsets
from .models import Modalidade, InscricaoCota
from .serializers import (
    ModalidadeSerializer,
    InscricaoCotaSerializer,
    InscricaoCotaCreateUpdateSerializer,
)


class ModalidadeViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista e detalhe das modalidades de cota (somente leitura)."""
    queryset = Modalidade.objects.all()
    serializer_class = ModalidadeSerializer


class InscricaoCotaViewSet(viewsets.ModelViewSet):
    """CRUD de inscrições cotistas."""
    queryset = InscricaoCota.objects.select_related('modalidade').prefetch_related(
        'dados_filhos_agentes', 'dados_pcd'
    )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return InscricaoCotaCreateUpdateSerializer
        return InscricaoCotaSerializer
