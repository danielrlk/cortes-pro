import streamlit as st
import os
import shutil
import yt_dlp
from moviepy.editor import VideoFileClip, clips_array
import numpy as np
import cv2
import mediapipe as mp
import socket

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Opus Mobile Factory", layout="wide", page_icon="🏭")

# Função para pegar o IP do computador (Para usar no celular)
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

# Configura FFmpeg
try:
    import imageio_ffmpeg
    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
    if not os.path.exists(local_ffmpeg):
        shutil.copy(imageio_ffmpeg.get_ffmpeg_exe(), local_ffmpeg)
    os.environ["IMAGEIO_FFMPEG_EXE"] = local_ffmpeg
except:
    pass

# --- 1. INTELIGÊNCIA ARTIFICIAL (Rastreio de Rosto) ---
def find_face_smart(video_path):
    mp_face_detection = mp.solutions.face_detection
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        faces_x, faces_y, faces_w = [], [], []
        timestamps = [2, 5, 10, 15, 20, 30, 45, 60] # Amostragem rápida
        
        for sec in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
            success, image = cap.read()
            if not success: break

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_detection.process(image)

            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    w_px = int(bbox.width * width)
                    h_px = int(bbox.height * height)
                    x_px = int(bbox.xmin * width)
                    y_px = int(bbox.ymin * height)
                    
                    faces_x.append(x_px + w_px//2)
                    faces_y.append(y_px + h_px//2)
                    faces_w.append(w_px)
                    break 
        cap.release()
        
        if len(faces_x) > 0:
            return (int(np.mean(faces_x)), int(np.mean(faces_y)), int(np.mean(faces_w)))
        return None

# --- 2. LAYOUT OPUS HD ---
def create_opus_layout(clip, face_data):
    W, H = clip.size
    TARGET_W, TARGET_H = 1080, 1920
    H_FACE = int(TARGET_H * 0.35)
    H_GAME = int(TARGET_H * 0.65)
    
    # WEBCAM
    if face_data:
        cx, cy, fw = face_data
        crop_size = int(fw * 3.2)
        crop_h = int(crop_size * (9/16))
        
        x1 = max(0, cx - crop_size//2)
        x2 = min(W, cx + crop_size//2)
        y1 = max(0, cy - crop_h//2)
        y2 = min(H, cy + crop_h//2)
        
        face_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
    else:
        face_clip = clip.crop(x1=0, y1=0, x2=W*0.4, y2=H*0.4)

    face_clip = face_clip.resize(width=TARGET_W)
    if face_clip.h < H_FACE: 
        face_clip = face_clip.resize(height=H_FACE)
        fw, fh = face_clip.size
        face_clip = face_clip.crop(x1=fw/2 - TARGET_W/2, x2=fw/2 + TARGET_W/2)
    else:
        fw, fh = face_clip.size
        face_clip = face_clip.crop(y1=fh/2 - H_FACE/2, y2=fh/2 + H_FACE/2)

    # GAMEPLAY
    gameplay = clip.crop(x1=W/2 - W*0.35, y1=0, x2=W/2 + W*0.35, y2=H)
    gameplay = gameplay.resize(height=H_GAME)
    if gameplay.w < TARGET_W: gameplay = gameplay.resize(width=TARGET_W)
    gw, gh = gameplay.size
    gameplay = gameplay.crop(x1=gw/2 - TARGET_W/2, y1=0, x2=gw/2 + TARGET_W/2, y2=H_GAME)
    
    return clips_array([[face_clip], [gameplay]])

# --- 3. DOWNLOADER HD ---
def download_video_hd(url):
    filename = "input_mobile_hd.mp4"
    if os.path.exists(filename): 
        try: os.remove(filename) 
        except: pass
        
    opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'ffmpeg_location': os.getcwd()
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return filename if os.path.exists(filename) else None

# --- 4. CAÇADOR DINÂMICO (Busca Infinita) ---
def analyze_dynamic_hunter(video_path, target_clips):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        audio = clip.audio.to_soundarray(fps=16000)
        if audio.ndim > 1: audio = audio.mean(axis=1)
        
        window = 8000
        energy = np.array([np.sqrt(np.mean(audio[i:i+window]**2)) for i in range(0, len(audio), window)])
        if len(energy) > 120: energy[:120] = 0 # Ignora intro (60s)
        
        cuts = []
        used = []
        
        # ESTRATÉGIA "LADEIRA": Começa exigente, vai descendo o nível até achar
        # Percentuais de exigência: 99% (Gritos), 95% (Falas altas), 80% (Falas normais), 50% (Qualquer coisa)
        thresholds = [99, 98, 95, 90, 85, 80, 70, 60, 50]
        
        for percentile in thresholds:
            if len(cuts) >= target_clips: break
            
            # Define o "Nível de Corte" atual
            limit = np.percentile(energy, percentile)
            peaks = np.where(energy > limit)[0]
            
            # Ordena pelos mais altos dentro desse nível
            peaks = sorted(peaks, key=lambda x: energy[x], reverse=True)
            
            for p in peaks:
                if len(cuts) >= target_clips: break
                t = p * 0.5
                
                # Regra de Distância: 30s entre clipes
                if not any(abs(t - u) < 30 for u in used):
                    s = max(0, t - 15)
                    e = min(duration, t + 30) # Clipes de 45s
                    cuts.append((s, e))
                    used.append(t)
        
        # ÚLTIMO RECURSO: Se ainda faltar, corta matematicamente no meio
        while len(cuts) < target_clips:
            t = (duration / (target_clips + 1)) * (len(cuts) + 1)
            cuts.append((t, t+45))
            
        clip.close()
        # Ordena cronologicamente
        return sorted(cuts, key=lambda x: x[0])
    except:
        return [(60, 105)] * target_clips

# --- INTERFACE ---
ip = get_local_ip()
st.markdown(f"""
<div style='background-color:#d4edda;padding:15px;border-radius:10px;border:1px solid #c3e6cb'>
    <h3 style='color:#155724;margin:0'>📱 MODO CELULAR ATIVO</h3>
    <p style='color:#155724;margin:0'>Para controlar pelo celular, conecte no Wi-Fi e acesse:</p>
    <h2 style='color:#155724;margin:5px 0'>http://{ip}:8501</h2>
</div>
""", unsafe_allow_html=True)

st.title("🏭 Opus Mobile Factory (Até 10 Clipes)")

url = st.text_input("Link do YouTube:")
# Aumentei o limite para 10
qtd = st.slider("Quantos Clipes Produzir?", 1, 10, 5)

if st.button("INICIAR FÁBRICA 🚀"):
    if not url:
        st.warning("Link?")
    else:
        status = st.status("🏭 Aquecendo os motores...", expanded=True)
        try:
            status.write("📥 Baixando Master (HD 1080p)...")
            path = download_video_hd(url)
            
            if path:
                status.write("👁️ Calibrando Mira Automática (MediaPipe)...")
                face_data = find_face_smart(path)
                
                status.write(f"🕵️ Caçando {qtd} momentos (Lógica Dinâmica)...")
                cuts = analyze_dynamic_hunter(path, qtd)
                
                status.write(f"✅ Encontrei {len(cuts)} clipes. Iniciando renderização em massa...")
                
                cols = st.columns(len(cuts))
                if len(cuts) > 3: cols = st.columns(3)
                
                progress_bar = st.progress(0)
                
                for i, (s, e) in enumerate(cuts):
                    out = f"clip_factory_{i+1}.mp4"
                    status.write(f"🔨 Renderizando Clip {i+1}/{len(cuts)}...")
                    
                    clip = VideoFileClip(path).subclip(s, e)
                    final = create_opus_layout(clip, face_data)
                    
                    final.write_videofile(out, codec='libx264', audio_codec='aac', bitrate="5000k", preset='ultrafast', logger=None)
                    
                    st.success(f"Clip {i+1} Pronto!")
                    st.video(out)
                    with open(out, "rb") as f: st.download_button(f"Baixar {i+1}", f, file_name=out)
                    
                    clip.close(); final.close()
                    progress_bar.progress((i + 1) / len(cuts))
                    
                status.update(label="FÁBRICA CONCLUÍDA! 🏭✨", state="complete")
            else:
                st.error("Erro no download.")
        except Exception as e:
            st.error(f"Erro: {e}")