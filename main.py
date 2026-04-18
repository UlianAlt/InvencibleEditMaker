import cv2
import numpy as np
import sys
import subprocess
import os
import math
import shutil

# --- CONFIGURAÇÕES FÁCEIS ---
FREQUENCIA_BALANCO = 10.0  
AMORTECIMENTO = 1.2        
ANGULO_MAXIMO = 70        
TEMPO_PARADA = 1.0       
PADDING = 200            
# ----------------------------

def get_resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, funcionando tanto em script quanto no executável."""
    if getattr(sys, 'frozen', False):
        # Se rodando como executável (PyInstaller)
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Se rodando como script .py
        return os.path.join(os.path.abspath("."), relative_path)

def get_ffmpeg_path():
    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    return "ffmpeg"

def aplicar_efeito(caminho_imagem, caminho_audio=None, output_final="resultado_final.mp4"):
    img = cv2.imread(caminho_imagem, cv2.IMREAD_UNCHANGED)
    if img is None:
        print("Erro: Imagem não encontrada.")
        return

    # Garante canal Alpha
    if img.shape[2] == 3:
        b, g, r = cv2.split(img)
        alpha = np.ones(b.shape, dtype=b.dtype) * 255
        img = cv2.merge([b, g, r, alpha])

    h, w, _ = img.shape
    new_w = w + (2 * PADDING)
    new_h = h + (2 * PADDING)
    canvas = np.zeros((new_h, new_w, 4), dtype=np.uint8)
    canvas[PADDING:PADDING+h, PADDING:PADDING+w] = img
    
    ponto_ancoragem = (new_w // 2, new_h - PADDING)
    fps = 30
    video_temp = "temp_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(video_temp, fourcc, fps, (new_w, new_h))

    print(f"Gerando animação...")
    
    i = 0
    frames_parados = 0
    angulo_anterior = 0
    
    while True:
        tempo = i / fps
        amplitude_atual = ANGULO_MAXIMO * math.exp(-AMORTECIMENTO * tempo)
        angulo = amplitude_atual * math.sin(FREQUENCIA_BALANCO * 2 * math.pi * tempo)
        
        if abs(amplitude_atual) < 0.5:
            frames_parados += 1
        else:
            frames_parados = 0
            
        if frames_parados > (fps * TEMPO_PARADA):
            break

        matriz_rotacao = cv2.getRotationMatrix2D(ponto_ancoragem, angulo, 1.0)
        img_rotacionada = cv2.warpAffine(canvas, matriz_rotacao, (new_w, new_h), 
                                         flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        
        fundo = np.zeros((new_h, new_w, 3), dtype=np.uint8)
        alpha_mask = img_rotacionada[:, :, 3] / 255.0
        rgb_img = img_rotacionada[:, :, :3]
        for c in range(3):
            fundo[:, :, c] = (1.0 - alpha_mask) * 0 + alpha_mask * rgb_img[:, :, c]
            
        if i > 0:
            vel_angular = abs(angulo - angulo_anterior)
            k_size = int(vel_angular * 0.5) * 2 + 1
            if k_size > 1:
                fundo = cv2.GaussianBlur(fundo, (k_size, k_size), 0)
        
        angulo_anterior = angulo
        video.write(fundo)
        i += 1

    video.release()

    # Finalização com ou sem áudio
    if caminho_audio and os.path.exists(caminho_audio):
        print(f"Adicionando áudio: {caminho_audio}...")
        ffmpeg_exec = get_ffmpeg_path()
        try:
            subprocess.run([
                ffmpeg_exec, '-y', '-i', video_temp, '-i', caminho_audio, 
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', 
                '-shortest', output_final
            ], check=True)
            os.remove(video_temp)
            print(f"Vídeo finalizado com áudio: {output_final}")
        except Exception as e:
            print(f"Erro ao usar FFmpeg: {e}")
    else:
        # Se não houver áudio, apenas renomeia o temp
        if os.path.exists(video_temp):
            shutil.move(video_temp, output_final)
            print(f"Vídeo finalizado (sem áudio): {output_final}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python script.py <imagem> [caminho_audio]")
    else:
        img_arg = sys.argv[1]
        # Se o segundo argumento existe, usa ele, senão, tenta buscar audio.mp3 no diretório/pacote
        audio_arg = sys.argv[2] if len(sys.argv) >= 3 else get_resource_path("audio.mp3")
        
        aplicar_efeito(img_arg, audio_arg)