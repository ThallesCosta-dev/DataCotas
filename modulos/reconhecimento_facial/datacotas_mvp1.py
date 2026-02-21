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
# 2. MOTORES DE ANÁLISE (CABELO, ROSTO, COR)
# ==========================================
def analyze_hair_texture(img_rgb, face_coords):
    """Estima a textura do cabelo pela densidade de bordas acima da testa.

    Retorna um score (0-100) e um rótulo heurístico (liso/ondulado/crespo).
    """
    x, y, w, h = face_coords
    # ROI do cabelo
    hair_y = max(0, y - int(h * 0.35))
    hair_h = int(h * 0.35)
    hair_roi = img_rgb[hair_y:y, x:x+w]
    
    if hair_roi.size == 0: return 0, "N/A"
    
    gray_hair = cv2.cvtColor(hair_roi, cv2.COLOR_RGB2GRAY)
    edges = cv2.Laplacian(gray_hair, cv2.CV_64F).var() 
    
    # Heurística simples
    texture_score = round(min(100, edges / 5.0), 1)
    label = "Crespo/Cacheado" if edges > 150 else "Ondulado" if edges > 60 else "Liso"
    return texture_score, label

def get_geometry(img_rgb):
    """Extrai métricas relativas de nariz e lábios via Face Mesh (MediaPipe).

    Se o MediaPipe não estiver disponível ou não houver face, retorna zeros.
    """
    if not HAS_MP: return 0, 0
    with mp_face_mesh.FaceMesh(static_image_mode=True) as mesh:
        res = mesh.process(img_rgb)
        if not res.multi_face_landmarks: return 0, 0
        l = res.multi_face_landmarks[0].landmark
        h, w = img_rgb.shape[:2]
        def p(i): return np.array([l[i].x * w, l[i].y * h])
        # Índices adimensionais (robustos a escala): nariz (largura/altura) e lábios (espessura relativa).
        n_w = np.linalg.norm(p(98)-p(327)); n_h = np.linalg.norm(p(168)-p(2))
        l_t = np.linalg.norm(p(0)-p(17))
        return round(n_w/n_h, 3), round(l_t/n_h, 3)

def get_skin_color(roi):
    """Extrai um tom de pele “base” via K-Means.

    Estratégia: clusterizar, converter para LAB e selecionar o 2º mais claro para reduzir
    impacto de highlight estourado e sombras profundas.
    """
    pix = cv2.resize(roi, (64,64)).reshape(-1,3)
    km = KMeans(5, n_init=10).fit(pix)
    cols = km.cluster_centers_.astype(int)
    labs = [color.rgb2lab(np.uint8([[c]]))[0][0] for c in cols]
    pairs = sorted([(labs[i][0], cols[i]) for i in range(5)], key=lambda x: x[0], reverse=True)
    return pairs[1][1]  

# ==========================================
# 3. PIPELINE DE EXECUÇÃO
# ==========================================
def process_candidato(path):
    """Processa uma imagem de candidato, extraíndo características fenotípicas.

    Retorna um dicionário com as características extraídas.
    """
    img = cv2.imread(path)
    if img is None: return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    f_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = f_cascade.detectMultiScale(gray, 1.1, 6)
    if len(faces) == 0: return None
    
    face = max(faces, key=lambda r: r[2]*r[3])
    x, y, w, h = face
    
    # 1) Cabelo: textura em ROI acima da testa
    hair_score, hair_type = analyze_hair_texture(rgb, face)
    
    # 2) Geometria: índices relativos
    nose_idx, lip_idx = get_geometry(rgb)
    
    # 3) Pele: ROIs nas bochechas (fração do bounding box do rosto)
    clx, cly, cw, ch = x+int(w*0.15), y+int(h*0.45), int(w*0.25), int(h*0.25)
    crx = x+int(w*0.60)
    roi = np.hstack((rgb[cly:cly+ch, clx:clx+cw], rgb[cly:cly+ch, crx:crx+cw]))
    dom_rgb = get_skin_color(roi)
    
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
    info = f"Cabelo: {hair_type} ({hair_score})\nNariz: {nose_idx} | Lábios: {lip_idx}"
    ax[3].text(0.1, 0.5, info, fontsize=12, color='white')
    ax[3].axis('off')
    plt.show()

    return {
        'Candidato': os.path.basename(path), 'MST_Score': mst_txt, 'Cor_HEX': mst_hex,
        'Cabelo_Tipo': hair_type, 'Cabelo_Densidade': hair_score,
        'Indice_Nasal': nose_idx, 'Proporcao_Labial': lip_idx, 'Luminancia_L': round(dom_lab[0], 2)
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