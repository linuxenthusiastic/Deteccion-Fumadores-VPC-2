"""
capturar_dataset_v3.py - Captura tipo "ráfaga" con ESPACIO sostenido

Comportamiento:
  - Mientras ESPACIO esté presionado, saca fotos cada RAFAGA_INTERVALO_MS ms
  - Cuando soltás ESPACIO, deja de disparar
  - Crea carpeta nueva automáticamente con timestamp
  - Se detiene automáticamente al llegar a MAX_FOTOS
  - Preview en vivo con feedback visual

Otros controles:
  q = salir
  r = reset contador (sin borrar fotos, empieza nueva carpeta)
"""

import cv2
import os
import time
from datetime import datetime

# ==================== CONFIGURACIÓN ====================
MAX_FOTOS = 100                   # límite de fotos (se detiene solo)
RAFAGA_INTERVALO_MS = 150         # tiempo entre fotos en ráfaga (ms)
RELEASE_TIMEOUT_MS = 200          # ms sin recibir tecla = "soltada"
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
BASE_OUTPUT_DIR = 'datasets'      # carpeta padre, dentro crea subcarpetas
# =======================================================

def crear_carpeta_nueva():
    """Crea una carpeta única con timestamp."""
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nueva = os.path.join(BASE_OUTPUT_DIR, f'captura_{timestamp}')
    os.makedirs(nueva, exist_ok=True)
    return nueva


def main():
    output_dir = crear_carpeta_nueva()
    print(f'\n{"="*55}')
    print(f'Carpeta de salida: {output_dir}')
    print(f'Límite: {MAX_FOTOS} fotos')
    print(f'{"="*55}')
    print('\nControles:')
    print('  ESPACIO (sostener) = ráfaga')
    print('  r = nueva carpeta (reset)')
    print('  q = salir\n')
    
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    
    if not cap.isOpened():
        print('ERROR: cámara no accesible')
        return
    
    foto_count = 0
    last_space_time = 0          # último timestamp de ESPACIO recibido
    last_capture_time = 0        # último timestamp de foto guardada
    burst_active = False         # si está en ráfaga ahora
    fps_smoothed = 0
    prev_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print('Error capturando frame')
            break
        
        now_ms = int(time.time() * 1000)
        
        # Detectar si ESPACIO sigue "presionado":
        # Si recibimos un evento de ESPACIO hace menos de RELEASE_TIMEOUT_MS, lo consideramos sostenido
        if (now_ms - last_space_time) < RELEASE_TIMEOUT_MS:
            burst_active = True
        else:
            burst_active = False
        
        # ----- Captura en ráfaga -----
        if burst_active and (now_ms - last_capture_time) >= RAFAGA_INTERVALO_MS:
            if foto_count < MAX_FOTOS:
                filename = os.path.join(output_dir, f'foto_{foto_count:04d}.jpg')
                cv2.imwrite(filename, frame)  # guardar SIN overlay
                foto_count += 1
                last_capture_time = now_ms
                print(f'  Foto {foto_count}/{MAX_FOTOS}')
        
        # ----- FPS para overlay -----
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if current_time != prev_time else 0
        fps_smoothed = 0.9 * fps_smoothed + 0.1 * fps
        prev_time = current_time
        
        # ----- Construir preview con overlay -----
        display = frame.copy()
        h, w = display.shape[:2]
        
        # Fondo semi-transparente arriba
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
        
        # Contador grande
        progreso = f'{foto_count} / {MAX_FOTOS}'
        cv2.putText(display, progreso,
                    (15, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        # Estado de ráfaga
        if burst_active:
            estado = 'GRABANDO'
            color_estado = (0, 0, 255)  # rojo
        else:
            estado = 'Mantené ESPACIO'
            color_estado = (200, 200, 200)
        
        cv2.putText(display, estado,
                    (15, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_estado, 2)
        
        # FPS arriba derecha
        cv2.putText(display, f'FPS {fps_smoothed:.0f}',
                    (w - 110, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)
        
        # Carpeta de destino abajo
        carpeta_label = os.path.basename(output_dir)
        cv2.putText(display, carpeta_label,
                    (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        
        # Borde rojo grueso cuando está en ráfaga
        if burst_active:
            cv2.rectangle(display, (0, 0), (w-1, h-1), (0, 0, 255), 6)
        
        # Si ya llegó al límite, mostrar mensaje
        if foto_count >= MAX_FOTOS:
            cv2.putText(display, 'LIMITE ALCANZADO - presiona q para salir o r para reset',
                        (15, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow('Captura Dataset - Rafaga con ESPACIO', display)
        
        # ----- Controles -----
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord(' '):
            last_space_time = now_ms  # actualizar timestamp de ESPACIO
        elif key == ord('r'):
            # Reset: nueva carpeta, contador en 0
            output_dir = crear_carpeta_nueva()
            foto_count = 0
            print(f'\n[RESET] Nueva carpeta: {output_dir}\n')
    
    cap.release()
    cv2.destroyAllWindows()
    print(f'\n{"="*55}')
    print(f'Fotos capturadas: {foto_count}')
    print(f'Guardadas en: {output_dir}')
    print(f'{"="*55}\n')


if __name__ == '__main__':
    main()
