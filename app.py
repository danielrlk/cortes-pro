import streamlit as st
import os
import shutil
import yt_dlp
from moviepy.editor import VideoFileClip, clips_array
import numpy as np
import cv2
import mediapipe as mp

st.set_page_config(page_title="Opus Mobile Factory Cloud", layout="wide", page_icon="☁️")

# --- 1. INTELIGÊNCIA ARTIFICIAL (Rastreio) ---
def find_face_smart(video_path):
    mp_face_detection = mp.solutions.face_detection
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        faces_x, faces_y, faces_w = [], [], []
        timestamps = [2, 5, 10, 15, 20, 30, 45, 60]
        
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

# --- 2. LAYOUT ---
def create_opus_layout(clip, face_data):
    W, H = clip.size
    TARGET_W, TARGET_H = 1080, 1920
    H_FACE = int(TARGET_H * 0.35)
    H_GAME = int(TARGET_H * 0.65)
    
    if face_data:
        cx, cy, fw = face_data
        crop_size = int(fw * 3.2)
        crop_h = int(crop_size * (9/16))
        x1, x2 = max(0, cx - crop_size//2), min(W, cx + crop_size//2)
        y1, y2 = max(0, cy - crop_h//2), min(H, cy + crop_h//2)
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

    gameplay = clip.crop(x1=W/2 - W*0.35, y1=0, x2=W/2 + W*0.35, y2=H)
    gameplay = gameplay.resize(height=H_GAME)
    if gameplay.w < TARGET_W: gameplay = gameplay.resize(width=TARGET_W)
    gw, gh = gameplay.size
    gameplay = gameplay.crop(x1=gw/2 - TARGET_W/2, y1=0, x2=gw/2 + TARGET_W/2, y2=H_GAME)
    
    return clips_array([[face_clip], [gameplay]])

# --- 3. DOWNLOADER DISFARÇADO (Fix Nuvem) ---
def download_video_hd(url):
    filename = "input_cloud.mp4"
    if os.path.exists(filename): 
        try: os.remove(filename) 
        except: pass
        
    opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        # TRUQUE 1: Fingir ser um Android para o YouTube não bloquear o IP da nuvem
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        # TRUQUE 2: User Agent de navegador real
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # NOTA: Removemos o 'ffmpeg_location' para ele usar o do sistema (packages.txt)
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return filename if os.path.exists(filename) else None

# --- 4. BUSCA DINÂMICA ---
def analyze_dynamic_hunter(video_path, target_clips):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        audio = clip.audio.to_soundarray(fps=16000)
        if audio.ndim > 1: audio = audio.mean(axis=1)
        
        window = 8000
        energy = np.array([np.sqrt(np.mean(audio[i:i+window]**2)) for i in range(0, len(audio), window)])
        if len(energy) > 120: energy[:120] = 0
        
        cuts, used = [], []
        thresholds = [99, 95, 90, 80, 70, 60]
        
        for percentile in thresholds:
            if len(cuts) >= target_clips: break
            limit = np.percentile(energy, percentile)
            peaks = sorted(np.where(energy > limit)[0], key=lambda x: energy[x], reverse=True)
            
            for p in peaks:
                if len(cuts) >= target_clips: break
                t = p * 0.5
                if not any(abs(t - u) < 30 for u in used):
                    cuts.append((max(0, t - 15), min(duration, t + 30)))
                    used.append(t)
        
        while len(cuts) < target_clips:
            t = (duration / (target_clips + 1)) * (len(cuts) + 1)
            cuts.append((t, t+45))
            
        clip.close()
        return sorted(cuts, key=lambda x: x[0])
    except:
        return [(60, 105)] * target_clips

# --- INTERFACE ---
st.title("☁️ Opus Cloud Factory")
url = st.text_input("Link do YouTube:")
qtd = st.slider("Quantidade:", 1, 5, 2)

if st.button("INICIAR NA NUVEM 🚀"):
    if not url:
        st.warning("Link?")
    else:
        status = st.status("Iniciando Servidor...", expanded=True)
        try:
            status.write("📥 Baixando (Modo Disfarçado Android)...")
            path = download_video_hd(url)
            
            if path:
                status.write("👁️ IA Google Detectando...")
                face_data = find_face_smart(path)
                
                status.write("✂️ Cortando...")
                cuts = analyze_dynamic_hunter(path, qtd)
                
                for i, (s, e) in enumerate(cuts):
                    out = f"clip_{i+1}.mp4"
                    status.write(f"Renderizando {i+1}...")
                    
                    clip = VideoFileClip(path).subclip(s, e)
                    final = create_opus_layout(clip, face_data)
                    final.write_videofile(out, codec='libx264', audio_codec='aac', bitrate="4000k", preset='ultrafast', logger=None)
                    
                    st.success(f"Clip {i+1}")
                    st.video(out)
                    with open(out, "rb") as f: st.download_button(f"Baixar {i+1}", f, file_name=out)
                    clip.close(); final.close()
                    
                status.update(label="PRONTO!", state="complete")
            else:
                st.error("Erro no Download: O YouTube bloqueou o IP da nuvem. Tente outro vídeo ou tente novamente em alguns minutos.")
        except Exception as e:
            st.error(f"Erro: {e}")
