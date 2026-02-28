from django.db import migrations, models
import django.db.models.deletion
import cotas.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Modalidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=50, unique=True)),
            ],
            options={
                'verbose_name': 'Modalidade de cota',
                'verbose_name_plural': 'Modalidades de cota',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='InscricaoCota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(blank=True, max_length=200)),
                ('rg', models.CharField(max_length=20)),
                ('cpf', models.CharField(max_length=14)),
                ('sexo', models.CharField(choices=[('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')], max_length=1)),
                ('comprovante_residencia', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('comprovante_residencia'))),
                ('historico_escolar', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('historico_escolar'))),
                ('certidao_nascimento', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('certidao_nascimento'))),
                ('titulo_eleitor', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('titulo_eleitor'))),
                ('foto_3x4', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('foto_3x4'))),
                ('reservista', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('reservista'))),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('modalidade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscricoes', to='cotas.modalidade')),
            ],
            options={
                'verbose_name': 'Inscrição cota',
                'verbose_name_plural': 'Inscrições cotas',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='FilhosAgentesSeguranca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cad_unico', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('filhos_agentes/cad_unico'))),
                ('decisao_administrativa', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('filhos_agentes/decisao_administrativa'))),
                ('certidao_obito', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('filhos_agentes/certidao_obito'))),
                ('comprovante_reforma_pensao', models.FileField(blank=True, null=True, upload_to=cotas.models.upload_inscricao('filhos_agentes/comprovante_reforma_pensao'))),
                ('inscricao', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dados_filhos_agentes', to='cotas.inscricaocota')),
            ],
            options={
                'verbose_name': 'Dados — Filhos de agentes de segurança',
                'verbose_name_plural': 'Dados — Filhos de agentes de segurança',
            },
        ),
    ]
