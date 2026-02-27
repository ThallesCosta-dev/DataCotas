from django.contrib import admin
from .models import Modalidade, InscricaoCota, FilhosAgentesSeguranca, AlunoPCD


@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'slug']


class FilhosAgentesSegurancaInline(admin.StackedInline):
    model = FilhosAgentesSeguranca
    extra = 0
    max_num = 1


class AlunoPCDInline(admin.StackedInline):
    model = AlunoPCD
    extra = 0
    max_num = 1


@admin.register(InscricaoCota)
class InscricaoCotaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'modalidade', 'sexo', 'criado_em']
    list_filter = ['modalidade', 'sexo']
    search_fields = ['nome', 'cpf', 'rg']
    inlines = [FilhosAgentesSegurancaInline, AlunoPCDInline]
