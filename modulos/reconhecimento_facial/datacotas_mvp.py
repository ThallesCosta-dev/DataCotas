import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from skimage import color
import math
import os
import glob
import csv

# ==========================================
# 1. ESCALA MONK CONTÍNUA (91 TONS)
# ==========================================
MONK_SCALE_HEX_ORIGINAL = [
    "#f6ede4", "#f3e7db", "#f7ead0", "#eadaba", "#d7bd96", 
    "#a07e56", "#825c43", "#604134", "#3a312a", "#292420"
]

def hex_to_rgb(hex_color):
    """Converte cor hexadecimal para RGB."""
    hex_color = hex_color.lstrip('#')
    return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])

def rgb_to_hex(rgb):
    """Converte cor RGB para hexadecimal, sanitizando valores."""
    r, g, b = np.clip(rgb, 0, 255)
    return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

# Gera tons intermediários por interpolação linear (passo 0.1 entre os âncoras).
EXTENDED_MONK_HEX = []
EXTENDED_MONK_TEXT = []
EXTENDED_MONK_RGB = []

# Interpola entre cada par de âncoras da escala original.
for i in range(len(MONK_SCALE_HEX_ORIGINAL) - 1):
    c1 = hex_to_rgb(MONK_SCALE_HEX_ORIGINAL[i])
    c2 = hex_to_rgb(MONK_SCALE_HEX_ORIGINAL[i+1])
    
    # Cria 10 passos entre um tom e outro (ex.: 6.0, 6.1, ..., 6.9).
    for step in range(10):
        fraction = step / 10.0
        c_inter = c1 * (1.0 - fraction) + c2 * fraction
        
        EXTENDED_MONK_RGB.append(c_inter)
        EXTENDED_MONK_HEX.append(rgb_to_hex(c_inter))
        
        score_value = (i + 1) + fraction
        EXTENDED_MONK_TEXT.append(f"MST {score_value:.1f}")

# Inclui o último tom âncora explicitamente (MST 10.0).
ultimo_tom = hex_to_rgb(MONK_SCALE_HEX_ORIGINAL[-1])
EXTENDED_MONK_RGB.append(ultimo_tom)
EXTENDED_MONK_HEX.append(rgb_to_hex(ultimo_tom))
EXTENDED_MONK_TEXT.append("MST 10.0")

# Pré-computa em CIELAB (espaço mais adequado para distância perceptual).
EXTENDED_MONK_LAB = [color.rgb2lab(np.uint8([[rgb]]))[0][0] for rgb in EXTENDED_MONK_RGB]

# ==========================================
# 2. FUNÇÕES DE PROCESSAMENTO E COLORIMETRIA
# ==========================================
def get_skin_color_smart(image, k=5):
    """Extrai um tom de pele base via K-Means.

    Seleciona o 2º cluster mais claro (em L* do LAB) para reduzir impacto de
    highlight estourado e de sombras/barba.
    """
    img_small = cv2.resize(image, (64, 64))
    pixels = img_small.reshape((-1, 3))
    
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(pixels)
    colors_rgb = kmeans.cluster_centers_.astype(int)
    
    colors_lab = [color.rgb2lab(np.uint8([[rgb]]))[0][0] for rgb in colors_rgb]
    
    luminance_rgb_pairs = []
    for i in range(k):
        lum = colors_lab[i][0]
        rgb = colors_rgb[i]
        luminance_rgb_pairs.append((lum, rgb))
    
    # 2º mais claro: equilíbrio entre superexposição e regiões escuras.
    luminance_rgb_pairs.sort(key=lambda x: x[0], reverse=True)
    return luminance_rgb_pairs[1][1]

def calculate_lab_distance(color1_lab, color2_lab):
    """Distância euclidiana em CIELAB."""
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1_lab, color2_lab)))

def match_monk_scale(dominant_rgb):
    dominant_lab = color.rgb2lab(np.uint8([[dominant_rgb]]))[0][0]
    
    distances = []
    for i, monk_lab in enumerate(EXTENDED_MONK_LAB):
        dist = calculate_lab_distance(dominant_lab, monk_lab)
        distances.append((dist, i))
    
    distances.sort()
    best_match_idx = distances[0][1]
    
    return EXTENDED_MONK_TEXT[best_match_idx], EXTENDED_MONK_HEX[best_match_idx], dominant_lab

# ==========================================
# 3. PIPELINE DE IMAGEM
# ==========================================
def process_image(image_path):
    img = cv2.imread(image_path)
    if img is None: return None
        
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(100, 100))
    if len(faces) == 0:
        print(f"Nenhum rosto detectado: {os.path.basename(image_path)}")
        return None
        
    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, box_w, box_h = largest_face
    
    # ROI nas bochechas baseada em frações do bounding box do rosto.
    cheek_l_x = x + int(box_w * 0.15)
    cheek_l_y = y + int(box_h * 0.45)
    cheek_w = int(box_w * 0.25)
    cheek_h = int(box_h * 0.25)
    
    cheek_r_x = x + int(box_w * 0.60)
    cheek_r_y = cheek_l_y 
    
    roi_left = img_rgb[cheek_l_y:cheek_l_y+cheek_h, cheek_l_x:cheek_l_x+cheek_w]
    roi_right = img_rgb[cheek_r_y:cheek_r_y+cheek_h, cheek_r_x:cheek_r_x+cheek_w]
    
    if roi_left.size == 0 or roi_right.size == 0: return None

    face_roi_combined = np.hstack((roi_left, roi_right))

    dominant_rgb = get_skin_color_smart(face_roi_combined)
    hex_dominant = '#%02x%02x%02x' % tuple(dominant_rgb)
    
    # Matching na escala MST por menor distância em CIELAB.
    monk_text, monk_hex, dominant_lab = match_monk_scale(dominant_rgb)
    
    # Visualização (inspeção manual / debug)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(12, 7))
    fig.suptitle(f'DataCotas - Análise: {os.path.basename(image_path)}', fontsize=16, fontweight='bold')
    
    ax1 = fig.add_subplot(1, 4, 1)
    img_plot = img_rgb.copy()
    cv2.rectangle(img_plot, (cheek_l_x, cheek_l_y), (cheek_l_x+cheek_w, cheek_l_y+cheek_h), (0, 255, 0), 3)
    cv2.rectangle(img_plot, (cheek_r_x, cheek_r_y), (cheek_r_x+cheek_w, cheek_r_y+cheek_h), (0, 255, 0), 3)
    ax1.imshow(img_plot)
    ax1.axis('off')
    ax1.set_title("Captura (Bochechas)")
    
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.imshow(face_roi_combined)
    ax2.axis('off')
    ax2.set_title("Área Combinada")
    
    ax3 = fig.add_subplot(1, 4, 3)
    dom_color_img = np.zeros((100, 100, 3), dtype=np.uint8)
    dom_color_img[:] = dominant_rgb
    ax3.imshow(dom_color_img)
    ax3.axis('off')
    ax3.set_title(f"Cor Extraída\n{hex_dominant}")
    
    ax4 = fig.add_subplot(1, 4, 4)
    monk_color_img = np.zeros((100, 100, 3), dtype=np.uint8)
    monk_color_img[:] = [int(monk_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
    ax4.imshow(monk_color_img)
    ax4.axis('off')
    ax4.set_title(f"Score Phenotípico:\n{monk_text}\n({monk_hex})")
    
    lab_text = f"Valores LAB: L*={dominant_lab[0]:.1f}, a*={dominant_lab[1]:.1f}, b*={dominant_lab[2]:.1f}"
    plt.figtext(0.5, 0.05, lab_text, ha="center", fontsize=11, bbox={"facecolor":"#444", "alpha":0.7, "pad":5})
    
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])
    plt.show()

    return {
        'Candidato': os.path.basename(image_path),
        'Cor_Extraida_HEX': hex_dominant,
        'Monk_Score': monk_text,
        'Monk_HEX': monk_hex,
        'LAB_L': round(dominant_lab[0], 2),
        'LAB_a': round(dominant_lab[1], 2),
        'LAB_b': round(dominant_lab[2], 2)
    }

# ==========================================
# EXECUÇÃO EM LOTE
# ==========================================
if __name__ == "__main__":
    pasta_candidatos = "candidatos"
    ficheiro_csv = "relatorio_banca.csv"
    
    if not os.path.exists(pasta_candidatos):
        print(f"Erro: A pasta '{pasta_candidatos}' não foi encontrada.")
    else:
        extensoes = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
        fotos = []
        for ext in extensoes:
            fotos.extend(glob.glob(os.path.join(pasta_candidatos, ext)))
        
        if not fotos:
            print(f"Nenhuma imagem encontrada na pasta '{pasta_candidatos}'.")
        else:
            print(f"Iniciando análise de {len(fotos)} candidatos na fila...")
            print("Dica: Feche a janela do gráfico para visualizar o próximo candidato.\n")
            resultados = []
            for caminho_da_foto in fotos:
                print(f"[Processando] -> {os.path.basename(caminho_da_foto)}")
                dados = process_image(caminho_da_foto)
                if dados: resultados.append(dados)
            
            if resultados:
                colunas = ['Candidato', 'Cor_Extraida_HEX', 'Monk_Score', 'Monk_HEX', 'LAB_L', 'LAB_a', 'LAB_b']
                try:
                    with open(ficheiro_csv, mode='w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=colunas)
                        writer.writeheader()
                        writer.writerows(resultados)
                    print(f"\nSucesso! Relatório salvo em: '{ficheiro_csv}'")
                except Exception as e: print(f"\nErro CSV: {e}")