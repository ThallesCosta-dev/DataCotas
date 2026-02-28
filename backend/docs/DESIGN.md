# DataCotas — Design do sistema de entrada de alunos cotistas

---

## Estrutura de dados

### 1. Documentos comuns (tipo pai)
Campos que **todas** as modalidades de cota compartilham:

| Campo | Tipo | Obrigatório | Observação |
|-------|------|-------------|------------|
| RG | Número (texto) | Sim | Apenas o número, não anexo |
| CPF | Número (texto) | Sim | Apenas o número, não anexo |
| Sexo | Escolha (M/F/outro) | Sim | Usado para regra do Reservista |
| Comprovante de residência | Anexo | Sim | |
| Histórico escolar | Anexo | Sim | |
| Certidão de nascimento | Anexo | Sim | |
| Título de eleitor | Anexo | Sim | |
| Foto 3x4 | Anexo | Sim | |
| Reservista | Anexo | Condicional | Obrigatório apenas para homens (conforme Sexo) |

---

### 2. Modalidades de cota (tipos específicos)

Cada modalidade herda/usa os documentos comuns e adiciona campos próprios.

#### 2.1 Filhos de agentes de segurança (mortos/incapacitados)
**Campos extras desta modalidade:**

| Campo | Tipo | Observação |
|-------|------|------------|
| CAD-ÚNICO | Anexo | Apenas documento (upload), não número |
| Decisão administrativa | Anexo | |
| Certidão de óbito | Anexo | |
| Comprovante de reforma/pensão | Anexo | |

#### 2.2 Aluno PCD
**Campos extras desta modalidade:**

| Campo | Tipo | Observação |
|-------|------|------------|
| Código CID | Texto (string) | ex: G80.9 |
| Laudo médico | Anexo PDF | Apenas PDF; validado na API |

---

## Definições de negócio (esclarecidas)
- **RG e CPF:** apenas número (campo texto), não são anexos.
- **Sexo:** armazenado para aplicar a regra de Reservista (obrigatório só para homens).
- **Modalidades futuras:** mesmo padrão — tipo pai + campos específicos por modalidade.
- **CAD-ÚNICO:** apenas anexo (documento), não há campo de número/código.

---

## Implementação (backend)
- [ ] Modelo “tipo pai”: dados comuns + uploads dos documentos comuns
- [ ] Tratamento de “Reservista” condicional (somente homens)
- [ ] Modelo da modalidade “Filhos de agentes de segurança” com campos extras
- [x] API REST /api/modalidades/ e /api/inscricoes/ (CRUD, multipart)
- [ ] Outras modalidades (a definir).

### Como rodar (Docker — use `sudo` se necessário)
```bash
sudo docker compose up -d db
sudo docker compose run --rm web python manage.py migrate
sudo docker compose up web
```
Ou com venv: `pip install -r requirements.txt` → `python manage.py migrate` → `python manage.py runserver`.

---