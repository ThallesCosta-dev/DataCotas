from rest_framework import serializers
from .models import Modalidade, InscricaoCota, FilhosAgentesSeguranca, AlunoPCD


class ModalidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modalidade
        fields = ['id', 'nome', 'slug']


class FilhosAgentesSegurancaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilhosAgentesSeguranca
        fields = [
            'id',
            'cad_unico',
            'decisao_administrativa',
            'certidao_obito',
            'comprovante_reforma_pensao',
        ]


class AlunoPCDSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlunoPCD
        fields = ['id', 'codigo_cid', 'laudo_medico']

    def validate_laudo_medico(self, value):
        if value and getattr(value, 'name', None) and not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('O laudo médico deve ser um arquivo PDF.')
        return value


class InscricaoCotaSerializer(serializers.ModelSerializer):
    modalidade_nome = serializers.CharField(source='modalidade.nome', read_only=True)
    dados_filhos_agentes = serializers.SerializerMethodField()
    dados_pcd = serializers.SerializerMethodField()

    class Meta:
        model = InscricaoCota
        fields = [
            'id',
            'modalidade',
            'modalidade_nome',
            'nome',
            'rg',
            'cpf',
            'sexo',
            'comprovante_residencia',
            'historico_escolar',
            'certidao_nascimento',
            'titulo_eleitor',
            'foto_3x4',
            'reservista',
            'criado_em',
            'atualizado_em',
            'dados_filhos_agentes',
            'dados_pcd',
        ]
        read_only_fields = ['criado_em', 'atualizado_em']

    def get_dados_filhos_agentes(self, obj):
        try:
            return FilhosAgentesSegurancaSerializer(obj.dados_filhos_agentes).data
        except FilhosAgentesSeguranca.DoesNotExist:
            return None

    def get_dados_pcd(self, obj):
        try:
            return AlunoPCDSerializer(obj.dados_pcd).data
        except AlunoPCD.DoesNotExist:
            return None


class InscricaoCotaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para criar/editar inscrição, aceitando dados aninhados por modalidade."""
    dados_filhos_agentes = FilhosAgentesSegurancaSerializer(required=False)
    dados_pcd = AlunoPCDSerializer(required=False)

    class Meta:
        model = InscricaoCota
        fields = [
            'id',
            'modalidade',
            'nome',
            'rg',
            'cpf',
            'sexo',
            'comprovante_residencia',
            'historico_escolar',
            'certidao_nascimento',
            'titulo_eleitor',
            'foto_3x4',
            'reservista',
            'criado_em',
            'atualizado_em',
            'dados_filhos_agentes',
            'dados_pcd',
        ]
        read_only_fields = ['criado_em', 'atualizado_em']

    def create(self, validated_data):
        dados_filhos = validated_data.pop('dados_filhos_agentes', None)
        dados_pcd = validated_data.pop('dados_pcd', None)
        inscricao = InscricaoCota.objects.create(**validated_data)
        if dados_filhos is not None and inscricao.modalidade.slug == 'filhos-agentes-seguranca':
            FilhosAgentesSeguranca.objects.create(inscricao=inscricao, **dados_filhos)
        if dados_pcd is not None and inscricao.modalidade.slug == 'aluno-pcd':
            AlunoPCD.objects.create(inscricao=inscricao, **dados_pcd)
        return inscricao

    def update(self, instance, validated_data):
        dados_filhos = validated_data.pop('dados_filhos_agentes', None)
        dados_pcd = validated_data.pop('dados_pcd', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if dados_filhos is not None and instance.modalidade.slug == 'filhos-agentes-seguranca':
            extras, _ = FilhosAgentesSeguranca.objects.get_or_create(inscricao=instance)
            for attr, value in dados_filhos.items():
                if value is not None:
                    setattr(extras, attr, value)
            extras.save()
        if dados_pcd is not None and instance.modalidade.slug == 'aluno-pcd':
            pcd, _ = AlunoPCD.objects.get_or_create(inscricao=instance)
            for attr, value in dados_pcd.items():
                if value is not None:
                    setattr(pcd, attr, value)
            pcd.save()
        return instance
