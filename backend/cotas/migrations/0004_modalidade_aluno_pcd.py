from django.db import migrations


def criar_modalidade_aluno_pcd(apps, schema_editor):
    Modalidade = apps.get_model('cotas', 'Modalidade')
    Modalidade.objects.get_or_create(
        slug='aluno-pcd',
        defaults={'nome': 'Aluno PCD'},
    )


def reverter(apps, schema_editor):
    Modalidade = apps.get_model('cotas', 'Modalidade')
    Modalidade.objects.filter(slug='aluno-pcd').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cotas', '0003_alunopcd'),
    ]

    operations = [
        migrations.RunPython(criar_modalidade_aluno_pcd, reverter),
    ]
