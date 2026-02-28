from django.db import models


def upload_inscricao(subdir):
    """Retorna callable para upload_to dos arquivos de inscrição."""
    def _upload(instance, filename):
        return f"cotas/inscricoes/{subdir}/{filename}"
    return _upload


class Modalidade(models.Model):
    """Modalidade de cota (ex: Filhos de agentes de segurança)."""
    nome = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Modalidade de cota'
        verbose_name_plural = 'Modalidades de cota'

    def __str__(self):
        return self.nome


class InscricaoCota(models.Model):
    """Dados comuns (tipo pai) de toda inscrição cotista."""
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]

    modalidade = models.ForeignKey(
        Modalidade,
        on_delete=models.PROTECT,
        related_name='inscricoes',
    )
    nome = models.CharField(max_length=200, blank=True)  
    rg = models.CharField(max_length=20)
    cpf = models.CharField(max_length=14)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)

 
    comprovante_residencia = models.FileField(
        upload_to=upload_inscricao('comprovante_residencia'),
        blank=True,
        null=True,
    )
    historico_escolar = models.FileField(
        upload_to=upload_inscricao('historico_escolar'),
        blank=True,
        null=True,
    )
    certidao_nascimento = models.FileField(
        upload_to=upload_inscricao('certidao_nascimento'),
        blank=True,
        null=True,
    )
    titulo_eleitor = models.FileField(
        upload_to=upload_inscricao('titulo_eleitor'),
        blank=True,
        null=True,
    )
    foto_3x4 = models.FileField(
        upload_to=upload_inscricao('foto_3x4'),
        blank=True,
        null=True,
    )
    reservista = models.FileField(
        upload_to=upload_inscricao('reservista'),
        blank=True,
        null=True,
    )  

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Inscrição cota'
        verbose_name_plural = 'Inscrições cotas'

    def __str__(self):
        return f"{self.nome or 'Sem nome'} ({self.modalidade}) — {self.cpf}"


class FilhosAgentesSeguranca(models.Model):
    """Campos extras da modalidade: Filhos de agentes de segurança (mortos/incapacitados)."""
    inscricao = models.OneToOneField(
        InscricaoCota,
        on_delete=models.CASCADE,
        related_name='dados_filhos_agentes',
    )
    cad_unico = models.FileField(
        upload_to=upload_inscricao('filhos_agentes/cad_unico'),
        blank=True,
        null=True,
    )
    decisao_administrativa = models.FileField(
        upload_to=upload_inscricao('filhos_agentes/decisao_administrativa'),
        blank=True,
        null=True,
    )
    certidao_obito = models.FileField(
        upload_to=upload_inscricao('filhos_agentes/certidao_obito'),
        blank=True,
        null=True,
    )
    comprovante_reforma_pensao = models.FileField(
        upload_to=upload_inscricao('filhos_agentes/comprovante_reforma_pensao'),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Dados — Filhos de agentes de segurança'
        verbose_name_plural = 'Dados — Filhos de agentes de segurança'

    def __str__(self):
        return f"Extras: {self.inscricao}"


class AlunoPCD(models.Model):
    """Campos extras da modalidade: Aluno PCD (pessoa com deficiência)."""
    inscricao = models.OneToOneField(
        InscricaoCota,
        on_delete=models.CASCADE,
        related_name='dados_pcd',
    )
    codigo_cid = models.CharField(max_length=20, blank=True)  
    laudo_medico = models.FileField(
        upload_to=upload_inscricao('aluno_pcd/laudo_medico'),
        blank=True,
        null=True,
    )  

    class Meta:
        verbose_name = 'Dados — Aluno PCD'
        verbose_name_plural = 'Dados — Aluno PCD'

    def __str__(self):
        return f"PCD: {self.inscricao} (CID {self.codigo_cid or '—'})"
