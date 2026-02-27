from django.db import migrations


def criar_modalidade_filhos_agentes(apps, schema_editor):
    Modalidade = apps.get_model('cotas', 'Modalidade')
    Modalidade.objects.get_or_create(
        slug='filhos-agentes-seguranca',
        defaults={'nome': 'Filhos de agentes de segurança (mortos/incapacitados)'},
    )


def reverter(apps, schema_editor):
    Modalidade = apps.get_model('cotas', 'Modalidade')
    Modalidade.objects.filter(slug='filhos-agentes-seguranca').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cotas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_modalidade_filhos_agentes, reverter),
    ]
