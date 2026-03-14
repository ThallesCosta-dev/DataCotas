import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from skimage import color, feature
import math
import os
import glob
import pandas as pd

# Inicialização segura do MediaPipe: se não estiver instalado, o pipeline segue sem métricas geométricas.
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    HAS_MP = True
except:
    HAS_MP = False

# ==========================================
# 1. ESCALA MONK CONTÍNUA (91 TONS)
# ==========================================
MONK_ORIGINAL = ["#f6ede4", "#f3e7db", "#f7ead0", "#eadaba", "#d7bd96", "#a07e56", "#825c43", "#604134", "#3a312a", "#292420"]
def h2r(h): 
    """Converte hexadecimal para RGB."""
    return np.array([int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)])
def r2h(rgb): 
    """Converte RGB para hexadecimal."""
    return '#{:02x}{:02x}{:02x}'.format(int(np.clip(rgb[0],0,255)), int(np.clip(rgb[1],0,255)), int(np.clip(rgb[2],0,255)))

EXT_MST_HEX, EXT_MST_TEXT, EXT_MST_RGB = [], [], []
for i in range(len(MONK_ORIGINAL) - 1):
    c1, c2 = h2r(MONK_ORIGINAL[i]), h2r(MONK_ORIGINAL[i+1])
    for s in range(10):
        f = s / 10.0
        c = c1*(1-f) + c2*f
        EXT_MST_RGB.append(c); EXT_MST_HEX.append(r2h(c)); EXT_MST_TEXT.append(f"MST {(i+1)+f:.1f}")
EXT_MST_RGB.append(h2r(MONK_ORIGINAL[-1])); EXT_MST_HEX.append(MONK_ORIGINAL[-1]); EXT_MST_TEXT.append("MST 10.0")
EXT_MST_LAB = [color.rgb2lab(np.uint8([[rgb]]))[0][0] for rgb in EXT_MST_RGB]

# ==========================================
# 2. VALIDAÇÃO QUALITATIVA DA IMAGEM
# ==========================================
def validate_image_quality(img, face_coords=None):
    """Valida a qualidade da imagem antes da análise.

    Verifica: nitidez, iluminação/sombra, brilho/contraste e obstruções faciais.
    Retorna (valido, mensagem) onde valido é booleano e mensagem descreve o problema.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # 1) Verificação de nitidez (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 50:
        return False, "Imagem muito desfocada. Por favor, envie uma foto mais nítida."
    
    # 2) Verificação de iluminação (brilho médio)
    mean_brightness = np.mean(gray)
    if mean_brightness < 40:
        return False, "Imagem muito escura. Por favor, melhore a iluminação."
    if mean_brightness > 220:
        return False, "Imagem muito clara/estourada. Por favor, reduza o brilho."
    
    # 3) Verificação de contraste (desvio padrão)
    std_dev = np.std(gray)
    if std_dev < 30:
        return False, "Imagem com baixo contraste. Por favor, ajuste a iluminação."
    
    # 4) Verificação de sombras (histogram analysis)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    dark_pixels = np.sum(hist[:50]) / (h * w)
    bright_pixels = np.sum(hist[200:]) / (h * w)
    
    if dark_pixels > 0.3:
        return False, "Imagem com excesso de sombras. Por favor, use iluminação uniforme."
    if bright_pixels > 0.2:
        return False, "Imagem com excesso de áreas brilhantes. Por favor, evite luz direta."
    
    # 5) Detecção de obstruções faciais (óculos, máscaras)
    if face_coords is not None:
        x, y, fw, fh = face_coords
        
        # ROI da área facial (olhos e boca)
        eyes_roi = gray[y+int(fh*0.2):y+int(fh*0.4), x:x+fw]
        mouth_roi = gray[y+int(fh*0.6):y+int(fh*0.8), x:x+fw]
        
        # Detecção de bordas verticais (possíveis óculos)
        if eyes_roi.size > 0:
            sobel_x = cv2.Sobel(eyes_roi, cv2.CV_64F, 1, 0, ksize=3)
            vertical_edges = np.mean(np.abs(sobel_x))
            if vertical_edges > 15:
                return False, "Detectada possível obstrução facial (óculos). Por favor, remova óculos."
        
        # Verificação de cobertura da boca (máscara)
        if mouth_roi.size > 0:
            mouth_variance = cv2.Laplacian(mouth_roi, cv2.CV_64F).var()
            if mouth_variance < 10:
                return False, "Detectada possível obstrução na região da boca. Por favor, remova máscaras."
    
    return True, "Imagem válida"

# ==========================================
# 3. NORMALIZAÇÃO DE IMAGEM
# ==========================================
def normalize_image(img):
    """Aplica normalização automática à imagem: ajuste de exposição, cor e contraste.

    Retorna a imagem normalizada para torná-la mais consistente para análise facial.
    """
    img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(img_lab)
    
    # Ajuste de contraste usando CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Normalização de cor (canais a e b)
    clahe_color = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    a = clahe_color.apply(a)
    b = clahe_color.apply(b)
    
    img_lab_norm = cv2.merge([l, a, b])
    img_norm = cv2.cvtColor(img_lab_norm, cv2.COLOR_LAB2BGR)
    
    # Ajuste de exposição via correção gamma
    gamma = 1.2
    img_gamma = np.power(img_norm / 255.0, gamma) * 255.0
    img_gamma = np.clip(img_gamma, 0, 255).astype(np.uint8)
    
    return img_gamma

# ==========================================
# 3. MOTORES DE ANÁLISE (CABELO, ROSTO, COR)
# ==========================================
def analyze_hair_texture(img_rgb, face_coords):
    """Estima a textura e cor do cabelo pela densidade de bordas e análise de cor.

    Retorna um score (0-100), rótulo heurístico e cor dominante do cabelo.
    """
    x, y, w, h = face_coords
    # ROI do cabelo
    hair_y = max(0, y - int(h * 0.35))
    hair_h = int(h * 0.35)
    hair_roi = img_rgb[hair_y:y, x:x+w]
    
    if hair_roi.size == 0: return 0, "N/A", (0, 0, 0)
    
    gray_hair = cv2.cvtColor(hair_roi, cv2.COLOR_RGB2GRAY)
    
    # Análise de textura múltipla
    laplacian_var = cv2.Laplacian(gray_hair, cv2.CV_64F).var()
    sobel_x = cv2.Sobel(gray_hair, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_hair, cv2.CV_64F, 0, 1, ksize=3)
    edge_density = np.mean(np.sqrt(sobel_x**2 + sobel_y**2))
    
    # Score combinado
    texture_score = round(min(100, (laplacian_var / 5.0 + edge_density * 2) / 2), 1)
    
    # Classificação mais granular
    if laplacian_var > 200 or edge_density > 30:
        label = "Crespo/Cacheado"
    elif laplacian_var > 100 or edge_density > 20:
        label = "Ondulado"
    elif laplacian_var > 50 or edge_density > 10:
        label = "Liso"
    else:
        label = "Muito Liso"
    
    # Análise de cor do cabelo
    hair_hsv = cv2.cvtColor(hair_roi, cv2.COLOR_RGB2HSV)
    hair_pixels = hair_hsv.reshape(-1, 3)
    
    # K-Means para encontrar cor dominante
    km = KMeans(3, n_init=10)
    km.fit(hair_pixels)
    dominant_color = km.cluster_centers_[np.argmax(np.bincount(km.labels_))]
    
    # Classificar cor do cabelo
    h, s, v = dominant_color
    if s < 30:
        hair_color = "Cinza/Prateado"
    elif h < 10 or h > 170:
        hair_color = "Ruivo"
    elif h < 25:
        hair_color = "Loiro"
    elif h < 35:
        hair_color = "Castanho Claro"
    elif h < 45:
        hair_color = "Castanho"
    else:
        hair_color = "Preto"
    
    return texture_score, label, hair_color

def get_geometry(img_rgb):
    """Extrai métricas relativas de nariz, lábios e formato facial via Face Mesh (MediaPipe).

    Se o MediaPipe não estiver disponível ou não houver face, retorna zeros.
    """
    if not HAS_MP: return 0, 0, 0, 0, 0
    with mp_face_mesh.FaceMesh(static_image_mode=True) as mesh:
        res = mesh.process(img_rgb)
        if not res.multi_face_landmarks: return 0, 0, 0, 0, 0
        l = res.multi_face_landmarks[0].landmark
        h, w = img_rgb.shape[:2]
        def p(i): return np.array([l[i].x * w, l[i].y * h])
        
        # Índices adimensionais (robustos a escala)
        # Nariz: largura/altura
        n_w = np.linalg.norm(p(98)-p(327))
        n_h = np.linalg.norm(p(168)-p(2))
        nose_idx = round(n_w/n_h, 3)
        
        # Lábios: espessura relativa
        l_t = np.linalg.norm(p(0)-p(17))
        lip_idx = round(l_t/n_h, 3)
        
        # Largura facial relativa
        face_width = np.linalg.norm(p(234)-p(454))
        face_height = np.linalg.norm(p(10)-p(152))
        face_ratio = round(face_width/face_height, 3)
        
        # Índice de simetria facial (diferença entre lados)
        left_eye = p(33)
        right_eye = p(263)
        nose_tip = p(1)
        left_dist = np.linalg.norm(left_eye - nose_tip)
        right_dist = np.linalg.norm(right_eye - nose_tip)
        symmetry_idx = round(abs(left_dist - right_dist) / max(left_dist, right_dist), 3)
        
        # Índice de formato de mandíbula
        jaw_left = p(234)
        jaw_right = p(454)
        chin = p(152)
        jaw_width = np.linalg.norm(jaw_left - jaw_right)
        jaw_height = np.linalg.norm(np.mean([jaw_left, jaw_right], axis=0) - chin)
        jaw_idx = round(jaw_width/jaw_height, 3)
        
        return nose_idx, lip_idx, face_ratio, symmetry_idx, jaw_idx

def get_skin_color(roi):
    """Extrai um tom de pele "base" via K-Means com análise de uniformidade.

    Estratégia: clusterizar, converter para LAB e selecionar o cluster mais representativo
    baseado em luminância e tamanho, reduzindo impacto de highlights e sombras.
    """
    # Redimensionar para análise
    pix = cv2.resize(roi, (64,64)).reshape(-1,3)
    
    # K-Means com mais clusters para melhor representação
    km = KMeans(7, n_init=10)
    km.fit(pix)
    cols = km.cluster_centers_.astype(int)
    
    # Converter para LAB
    labs = [color.rgb2lab(np.uint8([[c]]))[0][0] for c in cols]
    
    # Calcular tamanho de cada cluster
    cluster_sizes = np.bincount(km.labels_)
    
    # Selecionar cluster baseado em: luminância moderada + tamanho
    # Evita clusters muito escuros (sombras) ou muito claros (highlights)
    scores = []
    for i in range(7):
        l_val = labs[i][0]
        size = cluster_sizes[i]
        # Penaliza luminância muito baixa (< 30) ou muito alta (> 80)
        l_penalty = 0 if 30 <= l_val <= 80 else 10
        score = size - l_penalty
        scores.append(score)
    
    best_idx = np.argmax(scores)
    dom_rgb = cols[best_idx]
    
    # Calcular uniformidade da pele
    std_dev = np.std(pix[km.labels_ == best_idx], axis=0)
    uniformity = round(100 - np.mean(std_dev), 1)
    
    # Calcular tom de pele (quente/frio)
    dom_lab = labs[best_idx]
    a_val = dom_lab[1]  # Eixo verde-vermelho
    b_val = dom_lab[2]  # Eixo azul-amarelo
    
    if a_val > 5 and b_val > 5:
        skin_tone = "Quente (Amarelado)"
    elif a_val < -5 and b_val < -5:
        skin_tone = "Frio (Azulado)"
    elif a_val > 5:
        skin_tone = "Rosado"
    else:
        skin_tone = "Neutro"
    
    return dom_rgb, uniformity, skin_tone  

# ==========================================
# 3. PIPELINE DE EXECUÇÃO
# ==========================================
def process_candidato(path):
    """Processa uma imagem de candidato, extraíndo características fenotípicas.

    Retorna um dicionário com as características extraídas ou None se a validação falhar.
    """
    img = cv2.imread(path)
    if img is None: return None
    
    # Validação qualitativa da imagem antes do processamento
    is_valid, validation_msg = validate_image_quality(img)
    if not is_valid:
        print(f"[REJEITADO] {os.path.basename(path)}: {validation_msg}")
        return None
    
    # 4. Normalização da Imagem: ajustes automáticos de exposição, cor e contraste
    img_norm = normalize_image(img)
    
    rgb = cv2.cvtColor(img_norm, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img_norm, cv2.COLOR_BGR2GRAY)
    
    f_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = f_cascade.detectMultiScale(gray, 1.1, 6)
    if len(faces) == 0:
        print(f"[REJEITADO] {os.path.basename(path)}: Nenhuma face detectada")
        return None
    
    face = max(faces, key=lambda r: r[2]*r[3])
    x, y, w, h = face
    
    # Validação de obstruções faciais após detecção da face
    is_valid, obstruction_msg = validate_image_quality(img, face)
    if not is_valid:
        print(f"[REJEITADO] {os.path.basename(path)}: {obstruction_msg}")
        return None
    
    # 1) Cabelo: textura e cor em ROI acima da testa
    hair_score, hair_type, hair_color = analyze_hair_texture(rgb, face)
    
    # 2) Geometria: índices relativos (nariz, lábios, formato facial, simetria, mandíbula)
    nose_idx, lip_idx, face_ratio, symmetry_idx, jaw_idx = get_geometry(rgb)
    
    # 3) Pele: ROIs nas bochechas (fração do bounding box do rosto)
    clx, cly, cw, ch = x+int(w*0.15), y+int(h*0.45), int(w*0.25), int(h*0.25)
    crx = x+int(w*0.60)
    roi = np.hstack((rgb[cly:cly+ch, clx:clx+cw], rgb[cly:cly+ch, crx:crx+cw]))
    dom_rgb, skin_uniformity, skin_tone = get_skin_color(roi)
    
    # 4) Matching na escala MST via distância em CIELAB
    dom_lab = color.rgb2lab(np.uint8([[dom_rgb]]))[0][0]
    dists = sorted([(math.sqrt(sum((dom_lab-m)**2)), i) for i, m in enumerate(EXT_MST_LAB)])
    mst_txt, mst_hex = EXT_MST_TEXT[dists[0][1]], EXT_MST_HEX[dists[0][1]]

    # Visualização (debug/inspeção): ROI, match MST e métricas auxiliares
    plt.style.use('dark_background')
    fig, ax = plt.subplots(1, 4, figsize=(16, 6))
    fig.suptitle(f"DataCotas Full Phenotype: {os.path.basename(path)}", fontsize=15)
    
    temp_img = rgb.copy()
    cv2.rectangle(temp_img, (x,y), (x+w, y+h), (0,255,0), 2)
    ax[0].imshow(temp_img); ax[0].set_title("Detecção STF"); ax[0].axis('off')
    
    ax[1].imshow(roi); ax[1].set_title(f"Pele (L={dom_lab[0]:.1f})"); ax[1].axis('off')
    
    # Match MST
    m_img = np.zeros((100,100,3), dtype=np.uint8)
    m_img[:] = [int(mst_hex.lstrip('#')[i:i+2], 16) for i in (0,2,4)]
    ax[2].imshow(m_img); ax[2].set_title(f"Escala: {mst_txt}"); ax[2].axis('off')
    
    # Métricas (texto)
    info = (f"Cabelo: {hair_type} ({hair_score}) - {hair_color}\n"
            f"Nariz: {nose_idx} | Lábios: {lip_idx}\n"
            f"Formato: {face_ratio} | Simetria: {symmetry_idx}\n"
            f"Pele: {skin_tone} (Uniformidade: {skin_uniformity}%)")
    ax[3].text(0.1, 0.5, info, fontsize=11, color='white', va='center')
    ax[3].axis('off')
    plt.show()

    return {
        'Candidato': os.path.basename(path), 'MST_Score': mst_txt, 'Cor_HEX': mst_hex,
        'Cabelo_Tipo': hair_type, 'Cabelo_Densidade': hair_score, 'Cabelo_Cor': hair_color,
        'Indice_Nasal': nose_idx, 'Proporcao_Labial': lip_idx, 
        'Formato_Facial': face_ratio, 'Simetria_Facial': symmetry_idx, 'Indice_Mandibula': jaw_idx,
        'Tom_Pele': skin_tone, 'Uniformidade_Pele': skin_uniformity, 'Luminancia_L': round(dom_lab[0], 2)
    }

if __name__ == "__main__":
    pasta = "candidatos"
    if os.path.exists(pasta):
        fotos = []
        for e in ('*.jpg', '*.jpeg', '*.png'): fotos.extend(glob.glob(os.path.join(pasta, e)))
        if fotos:
            print(f"Iniciando Análise Fenotípica STF em {len(fotos)} arquivos...")
            res = [process_candidato(f) for f in fotos if process_candidato(f) is not None]
            pd.DataFrame(res).to_excel("relatorio_datacotas_stf.xlsx", index=False)
            print("\nFinalizado! Planilha 'relatorio_datacotas_stf.xlsx' gerada.")