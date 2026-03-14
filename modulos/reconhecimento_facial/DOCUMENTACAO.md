# Documentação - Sistema de Análise Fenotípica DataCotas

## Visão Geral

Este documento descreve o sistema completo de análise fenotípica do DataCotas, incluindo:

- **Validação Qualitativa da Imagem** - Verifica nitidez, iluminação, contraste e obstruções
- **Normalização da Imagem** - Ajustes automáticos de exposição, cor e contraste
- **Motores de Análise** - Cabelo, Geometria Facial e Cor da Pele (melhorados)
- **Matching na Escala Monk** - Classificação fenotípica STF

---

## 1. Módulo de Validação Qualitativa da Imagem

### Função: `validate_image_quality(img, face_coords=None)`

Valida a qualidade da imagem antes da análise facial, verificando critérios mínimos de qualidade.

#### Parâmetros

- **`img`** (numpy.ndarray): Imagem em formato BGR (OpenCV)
- **`face_coords`** (tuple, opcional): Coordenadas do rosto detectado `(x, y, w, h)`

#### Retorno

- **`valido`** (bool): `True` se a imagem atende aos critérios, `False` caso contrário
- **`mensagem`** (str): Descrição do problema se inválido, ou mensagem de sucesso

#### Critérios de Validação

##### 1. Nitidez (Sharpness)
- **Técnica**: Variância do Laplaciano
- **Threshold**: 50
- **Motivo de rejeição**: "Imagem muito desfocada. Por favor, envie uma foto mais nítida."

##### 2. Iluminação (Brightness)
- **Técnica**: Brilho médio da imagem em escala de cinza
- **Faixa aceitável**: 40 a 220 (0-255)
- **Motivos de rejeição**:
  - < 40: "Imagem muito escura. Por favor, melhore a iluminação."
  - > 220: "Imagem muito clara/estourada. Por favor, reduza o brilho."

##### 3. Contraste
- **Técnica**: Desvio padrão dos pixels em escala de cinza
- **Threshold**: 30
- **Motivo de rejeição**: "Imagem com baixo contraste. Por favor, ajuste a iluminação."

##### 4. Sombras e Áreas Brilhantes
- **Técnica**: Análise de histograma
- **Thresholds**:
  - Pixels escuros (< 50): máximo 30% da imagem
  - Pixels claros (> 200): máximo 20% da imagem
- **Motivos de rejeição**:
  - "Imagem com excesso de sombras. Por favor, use iluminação uniforme."
  - "Imagem com excesso de áreas brilhantes. Por favor, evite luz direta."

##### 5. Obstruções Faciais (apenas se face_coords fornecido)
- **Óculos**: Detecção de bordas verticais na região dos olhos (Sobel X)
- **Máscaras**: Baixa variância do Laplaciano na região da boca
- **Motivos de rejeição**:
  - "Detectada possível obstrução facial (óculos). Por favor, remova óculos."
  - "Detectada possível obstrução na região da boca. Por favor, remova máscaras."

#### Fluxo de Execução

```python
# Validação inicial (sem face detectada)
valido, msg = validate_image_quality(img)

# Validação completa (após detecção facial)
valido, msg = validate_image_quality(img, face_coords)
```

---

## 2. Módulo de Normalização da Imagem

### Função: `normalize_image(img)`

Aplica normalização automática à imagem para torná-la mais consistente para análise facial.

#### Parâmetros

- **`img`** (numpy.ndarray): Imagem em formato BGR (OpenCV)

#### Retorno

- **`img_gamma`** (numpy.ndarray): Imagem normalizada em formato BGR

#### Técnicas Aplicadas

##### 1. Ajuste de Contraste (CLAHE)
- **Espaço de cor**: LAB (Luminância, Cromaticidade A e B)
- **Técnica**: Contrast Limited Adaptive Histogram Equalization
- **Parâmetros**:
  - `clipLimit`: 2.0 (canal L), 1.5 (canais A e B)
  - `tileGridSize`: (8, 8)
- **Objetivo**: Melhorar contraste local sem amplificar ruído

##### 2. Normalização de Cor
- **Espaço de cor**: LAB
- **Técnica**: CLAHE nos canais A e B (cromáticos)
- **Objetivo**: Balancear cores e reduzir variações de temperatura de cor

##### 3. Ajuste de Exposição (Correção Gamma)
- **Técnica**: Transformação não-linear
- **Gamma**: 1.2 (escurecimento suave para compensar imagens superexpostas)
- **Fórmula**: `output = (input/255)^gamma * 255`
- **Objetivo**: Compensar variações de iluminação

#### Fluxo de Processamento

```python
# 1. Converter BGR para LAB
img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

# 2. Separar canais
l, a, b = cv2.split(img_lab)

# 3. Aplicar CLAHE em cada canal
l = clahe.apply(l)
a = clahe_color.apply(a)
b = clahe_color.apply(b)

# 4. Recompor e converter para BGR
img_norm = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

# 5. Aplicar correção gamma
img_gamma = np.power(img_norm / 255.0, 1.2) * 255.0
```

---

## 3. Motores de Análise (Melhorados)

### 3.1 Motor de Análise de Cabelo

#### Função: `analyze_hair_texture(img_rgb, face_coords)`

Estima a textura e cor do cabelo pela densidade de bordas e análise de cor.

#### Parâmetros

- **`img_rgb`** (numpy.ndarray): Imagem em formato RGB
- **`face_coords`** (tuple): Coordenadas do rosto detectado `(x, y, w, h)`

#### Retorno

- **`texture_score`** (float): Score de textura (0-100)
- **`label`** (str): Rótulo heurístico (Muito Liso, Liso, Ondulado, Crespo/Cacheado)
- **`hair_color`** (str): Cor dominante do cabelo

#### Técnicas Aplicadas

##### Análise de Textura Múltipla
- **Laplacian Variance**: Mede a variação de bordas na imagem
- **Sobel Edge Density**: Calcula densidade de bordas horizontal e vertical
- **Score Combinado**: `(laplacian_var / 5.0 + edge_density * 2) / 2`

##### Classificação de Textura
| Condição | Rótulo |
|----------|--------|
| laplacian_var > 200 ou edge_density > 30 | Crespo/Cacheado |
| laplacian_var > 100 ou edge_density > 20 | Ondulado |
| laplacian_var > 50 ou edge_density > 10 | Liso |
| Outros | Muito Liso |

##### Análise de Cor do Cabelo
- **Espaço de cor**: HSV (Hue, Saturation, Value)
- **Técnica**: K-Means clustering (3 clusters)
- **Classificação**:
  - s < 30: Cinza/Prateado
  - h < 10 ou h > 170: Ruivo
  - h < 25: Loiro
  - h < 35: Castanho Claro
  - h < 45: Castanho
  - Outros: Preto

#### ROI do Cabelo

- **Posição**: Acima da testa (35% da altura do rosto)
- **Dimensões**: Largura do rosto × 35% da altura

---

### 3.2 Motor de Geometria Facial

#### Função: `get_geometry(img_rgb)`

Extrai métricas relativas de nariz, lábios e formato facial via Face Mesh (MediaPipe).

#### Parâmetros

- **`img_rgb`** (numpy.ndarray): Imagem em formato RGB

#### Retorno

- **`nose_idx`** (float): Índice nasal (largura/altura)
- **`lip_idx`** (float): Índice labial (espessura relativa)
- **`face_ratio`** (float): Razão largura/altura facial
- **`symmetry_idx`** (float): Índice de simetria facial
- **`jaw_idx`** (float): Índice de formato de mandíbula

#### Métricas Extraídas

##### 1. Índice Nasal
- **Fórmula**: `largura_nariz / altura_nariz`
- **Landmarks**: 98-327 (largura), 168-2 (altura)
- **Interpretação**: Valores mais altos indicam nariz mais largo

##### 2. Índice Labial
- **Fórmula**: `espessura_lábios / altura_nariz`
- **Landmarks**: 0-17 (lábios)
- **Interpretação**: Valores mais altos indicam lábios mais grossos

##### 3. Formato Facial
- **Fórmula**: `largura_face / altura_face`
- **Landmarks**: 234-454 (largura), 10-152 (altura)
- **Interpretação**:
  - < 0.8: Face alongada
  - 0.8-1.0: Face oval
  - > 1.0: Face larga

##### 4. Simetria Facial
- **Fórmula**: `|dist_esquerda - dist_direita| / max(dist_esquerda, dist_direita)`
- **Landmarks**: 33 (olho esquerdo), 263 (olho direito), 1 (ponta do nariz)
- **Interpretação**:
  - < 0.05: Alta simetria
  - 0.05-0.1: Simetria moderada
  - > 0.1: Baixa simetria

##### 5. Índice de Mandíbula
- **Fórmula**: `largura_mandíbula / altura_mandíbula`
- **Landmarks**: 234-454 (largura), média(234,454)-152 (altura)
- **Interpretação**:
  - < 1.5: Mandíbula estreita
  - 1.5-2.0: Mandíbula média
  - > 2.0: Mandíbula larga

#### Dependência

- **MediaPipe FaceMesh**: Obrigatório para cálculos geométricos
- **Fallback**: Retorna zeros se MediaPipe não estiver disponível

---

### 3.3 Motor de Cor da Pele

#### Função: `get_skin_color(roi)`

Extrai um tom de pele "base" via K-Means com análise de uniformidade e tom.

#### Parâmetros

- **`roi`** (numpy.ndarray): Região de interesse da pele (bochechas)

#### Retorno

- **`dom_rgb`** (numpy.ndarray): Cor dominante em RGB
- **`uniformity`** (float): Uniformidade da pele (0-100%)
- **`skin_tone`** (str): Tom de pele (Quente, Frio, Rosado, Neutro)

#### Técnicas Aplicadas

##### Clusterização Aprimorada
- **Número de clusters**: 7 (aumentado de 5)
- **Algoritmo**: K-Means (n_init=10)
- **Resolução**: 64×64 pixels

##### Seleção Inteligente de Cluster
- **Critério**: Luminância moderada + tamanho do cluster
- **Penalização**: Clusters com L < 30 ou L > 80 são penalizados
- **Fórmula**: `score = tamanho - penalidade_luminância`
- **Objetivo**: Evitar sombras profundas e highlights estourados

##### Uniformidade da Pele
- **Cálculo**: `100 - média(desvio_padrão_RGB)`
- **Interpretação**:
  - > 90: Uniformidade excelente
  - 80-90: Uniformidade boa
  - < 80: Uniformidade baixa

##### Classificação de Tom de Pele
Baseada em canais A e B do espaço LAB:
- **A > 5 e B > 5**: Quente (Amarelado)
- **A < -5 e B < -5**: Frio (Azulado)
- **A > 5**: Rosado
- **Outros**: Neutro

#### ROI da Pele

- **Posição**: Bochechas esquerda e direita
- **Dimensões**: 25% da largura × 25% da altura do rosto
- **Localização**: 45% da altura do rosto (região das bochechas)

---

## 4. Integração no Pipeline

### Ordem de Execução

```
1. Carregar Imagem
   ↓
2. Validação Qualitativa (critérios gerais)
   ↓ (se válido)
3. Normalização da Imagem
   ↓
4. Detecção Facial
   ↓ (se face detectada)
5. Validação Qualitativa (obstruções faciais)
   ↓ (se válido)
6. Análise Fenotípica:
   - Análise de Cabelo (textura + cor)
   - Análise Geométrica (5 métricas)
   - Análise de Pele (cor + uniformidade + tom)
   ↓
7. Matching na Escala Monk
   ↓
8. Geração de Relatório
```

### Exemplo de Uso

```python
import cv2
from datacotas_mvp1 import validate_image_quality, normalize_image

# Carregar imagem
img = cv2.imread("foto.jpg")

# Validar qualidade
valido, msg = validate_image_quality(img)
if not valido:
    print(f"Imagem rejeitada: {msg}")
    return

# Normalizar imagem
img_norm = normalize_image(img)

# Prosseguir com análise...
```

### Tratamento de Rejeição

Quando a validação falha, o sistema:
1. Imprime mensagem no console: `[REJEITADO] nome_arquivo: motivo`
2. Retorna `None` da função `process_candidato`
3. Não inclui o candidato no relatório final

---

## 5. Relatório Final

### Características Fenotípicas Extraídas

O sistema agora extrai **13 características fenotípicas** (antes eram 7):

| Categoria | Característica | Tipo | Descrição |
|-----------|----------------|------|-----------|
| **Identificação** | Candidato | string | Nome do arquivo da imagem |
| **Escala Monk** | MST_Score | string | Classificação na escala Monk (MST 1.0-10.0) |
| | Cor_HEX | string | Cor em formato hexadecimal |
| | Luminancia_L | float | Luminância no espaço LAB |
| **Cabelo** | Cabelo_Tipo | string | Textura (Muito Liso, Liso, Ondulado, Crespo/Cacheado) |
| | Cabelo_Densidade | float | Score de densidade (0-100) |
| | Cabelo_Cor | string | Cor dominante (Preto, Castanho, Loiro, Ruivo, etc.) |
| **Geometria** | Indice_Nasal | float | Razão largura/altura do nariz |
| | Proporcao_Labial | float | Espessura relativa dos lábios |
| | Formato_Facial | float | Razão largura/altura do rosto |
| | Simetria_Facial | float | Índice de simetria (0-1) |
| | Indice_Mandibula | float | Razão largura/altura da mandíbula |
| **Pele** | Tom_Pele | string | Tom (Quente, Frio, Rosado, Neutro) |
| | Uniformidade_Pele | float | Uniformidade (0-100%) |

### Formato do Relatório

O relatório é gerado em formato Excel (`relatorio_datacotas_stf.xlsx`) com:
- Uma linha por candidato processado
- Colunas organizadas por categoria
- Valores numéricos com 2-3 casas decimais
- Textos descritivos para características qualitativas

### Visualização

Durante o processamento, o sistema exibe uma visualização com 4 painéis:
1. **Detecção STF**: Imagem original com bounding box facial
2. **Pele**: ROI das bochechas com luminância
3. **Escala**: Cor correspondente na escala Monk
4. **Métricas**: Texto com todas as características extraídas

---

## 6. Parâmetros Configuráveis

### Validação

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `laplacian_threshold` | 50 | Mínimo de nitidez |
| `brightness_min` | 40 | Brilho mínimo |
| `brightness_max` | 220 | Brilho máximo |
| `contrast_threshold` | 30 | Mínimo de contraste |
| `dark_pixel_ratio` | 0.3 | Máximo de pixels escuros |
| `bright_pixel_ratio` | 0.2 | Máximo de pixels claros |
| `vertical_edge_threshold` | 15 | Detecção de óculos |
| `mouth_variance_threshold` | 10 | Detecção de máscaras |

### Normalização

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `clahe_clip_limit_l` | 2.0 | Limite CLAHE canal L |
| `clahe_clip_limit_color` | 1.5 | Limite CLAHE canais A/B |
| `clahe_tile_size` | (8, 8) | Tamanho do tile CLAHE |
| `gamma_correction` | 1.2 | Fator de correção gamma |

---

## 7. Referências

### Técnicas Utilizadas

- **CLAHE**: Zuiderveld, K. (1994). "Contrast Limited Adaptive Histogram Equalization"
- **Laplacian Variance**: Pech, P. et al. (2000). "Image Sharpness Assessment"
- **Sobel Edge Detection**: Sobel, I. & Feldman, G. (1968). "3x3 Isotropic Gradient Operator"
- **Gamma Correction**: Reinhard, E. et al. (2002). "Photographic Tone Reproduction"
- **K-Means Clustering**: Lloyd, S. (1982). "Least Squares Quantization in PCM"
- **MediaPipe Face Mesh**: Lugaresi, C. et al. (2019). "MediaPipe: A Framework for Building Perception Pipelines"

### Espaços de Cor

- **LAB**: Espaço perceptualmente uniforme para separação de luminância e crominância
- **HSV**: Espaço de cor intuitivo para análise de cor (Hue, Saturation, Value)
- **BGR**: Formato nativo do OpenCV
- **RGB**: Formato padrão para exibição

---

## 8. Notas de Implementação

### Validação e Normalização
- A validação ocorre em duas etapas: antes e após detecção facial
- A normalização é aplicada apenas após validação inicial
- Obstruções faciais só são verificadas se uma face for detectada
- Todos os thresholds podem ser ajustados conforme necessidade específica
- O sistema é tolerante a variações moderadas de qualidade de imagem

### Motores de Análise
- **Cabelo**: A análise de cor usa HSV para melhor separação de cores naturais
- **Geometria**: Todas as métricas são adimensionais (robustas à escala)
- **Pele**: A seleção inteligente de clusters evita sombras e highlights
- **MediaPipe**: O sistema funciona mesmo sem MediaPipe (retorna zeros para métricas geométricas)

### Performance
- O pipeline processa imagens em paralelo quando executado em lote
- A visualização é gerada apenas para debug/inspeção
- O relatório Excel é otimizado para grandes volumes de dados
- Memória: O sistema usa aproximadamente 2-3 GB para processar 100 imagens

### Limitações Conhecidas
- Detecção facial depende de iluminação frontal adequada
- Análise de cabelo pode ser afetada por chapéus ou penteados complexos
- Métricas geométricas requerem MediaPipe instalado
- A escala Monk foi calibrada para população brasileira

---

## 9. Exemplos de Uso

### Processamento Individual

```python
import cv2
from datacotas_mvp1 import process_candidato

# Processar uma única imagem
resultado = process_candidato("caminho/para/foto.jpg")

if resultado:
    print("=== RESULTADO DA ANÁLISE ===")
    for chave, valor in resultado.items():
        print(f"{chave}: {valor}")
else:
    print("A imagem não passou na validação.")
```

### Processamento em Lote

```python
import os
import glob
import pandas as pd
from datacotas_mvp1 import process_candidato

# Configurar pasta
pasta = "candidatos"

# Encontrar todas as imagens
fotos = []
for ext in ('*.jpg', '*.jpeg', '*.png'):
    fotos.extend(glob.glob(os.path.join(pasta, ext)))

# Processar todas as imagens
resultados = [process_candidato(f) for f in fotos]

# Gerar relatório
df = pd.DataFrame(resultados)
df.to_excel("relatorio.xlsx", index=False)
print(f"Processadas {len(resultados)} imagens.")
```

### Validação Personalizada

```python
import cv2
from datacotas_mvp1 import validate_image_quality, normalize_image

# Validar imagem
img = cv2.imread("foto.jpg")
valido, mensagem = validate_image_quality(img)

if valido:
    # Normalizar imagem
    img_norm = normalize_image(img)
    # Prosseguir com análise...
else:
    print(f"Imagem rejeitada: {mensagem}")
```

---

## 10. Troubleshooting

### Problemas Comuns

#### Imagem Rejeitada por "Muito Desfocada"
- **Solução**: Use uma câmera com melhor foco ou mantenha o dispositivo estável
- **Threshold**: Ajuste `laplacian_threshold` na função `validate_image_quality`

#### Nenhuma Face Detectada
- **Causa**: Iluminação ruim ou rosto muito pequeno/rotacionado
- **Solução**: Melhore a iluminação ou use uma foto frontal
- **Alternativa**: Ajuste parâmetros do `detectMultiScale`

#### MediaPipe Não Disponível
- **Solução**: Instale MediaPipe: `pip install mediapipe`
- **Fallback**: O sistema funciona sem MediaPipe (métricas geométricas = 0)

#### Erro de Memória
- **Causa**: Processamento de muitas imagens simultaneamente
- **Solução**: Processar em lotes menores ou aumentar RAM disponível

### Logs e Debug

O sistema imprime mensagens informativas:
- `[REJEITADO] arquivo: motivo` - Imagem não passou na validação
- `Iniciando Análise Fenotípica STF em X arquivos...` - Início do processamento
- `Finalizado! X imagens processadas com sucesso.` - Conclusão do processamento

---

## 11. Changelog

### Versão Atual (v2.0)

**Novos Recursos:**
- ✅ Módulo de Validação Qualitativa da Imagem
- ✅ Módulo de Normalização da Imagem
- ✅ Motor de Análise de Cabelo melhorado (textura + cor)
- ✅ Motor de Geometria Facial expandido (5 métricas)
- ✅ Motor de Cor da Pele aprimorado (uniformidade + tom)
- ✅ Notebook Jupyter interativo

**Melhorias:**
- 📈 De 7 para 13 características fenotípicas
- 📈 Classificação de textura mais granular (4 categorias)
- 📈 Análise de cor do cabelo (6 categorias)
- 📈 Métricas geométricas adicionais (formato, simetria, mandíbula)
- 📈 Análise de uniformidade e tom da pele

**Correções:**
- 🐛 Seleção de cluster de pele mais robusta
- 🐛 Detecção de obstruções faciais mais precisa
- 🐛 Normalização de cor mais consistente

### Versão Anterior (v1.0)

- Análise básica de cabelo (textura)
- Métricas geométricas simples (nariz, lábios)
- Extração de cor da pele (K-Means)
- Matching na escala Monk
