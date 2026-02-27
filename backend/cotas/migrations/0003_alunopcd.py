from django.db import migrations, models
import django.db.models.deletion
import cotas.models


class Migration(migrations.Migration):

    dependencies = [
        ('cotas', '0002_modalidade_filhos_agentes_seguranca'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlunoPCD',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_cid', models.CharField(blank=True, max_length=20)),
                ('laudo_medico', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('aluno_pcd/laudo_medico'))),
                ('inscricao', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dados_pcd', to='cotas.inscricaocota')),
            ],
            options={
                'verbose_name': 'Dados — Aluno PCD',
                'verbose_name_plural': 'Dados — Aluno PCD',
            },
        ),
    ]
