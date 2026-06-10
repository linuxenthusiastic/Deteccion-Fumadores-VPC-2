"""
Backend Flask para demo de detección de cigarros en vivo
Tema: cámara de seguridad de cajero automático

Uso:
    python app.py
    Abrir http://localhost:5000 en el navegador
"""

import cv2
import time
import threading
from datetime import datetime
from collections import deque
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO

# ==================== CONFIGURACIÓN ====================
MODEL_PATH = 'best.pt'
CAMERA_INDEX = 0
CONF_THRESHOLD = 0.4
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
INFERENCE_SIZE = 320
PROCESS_EVERY_N_FRAMES = 2
# =======================================================

app = Flask(__name__)

# Estado compartido (thread-safe con lock)
state_lock = threading.Lock()
state = {
    'fps': 0.0,
    'detections': 0,
    'total_detections_session': 0,
    'alerts': deque(maxlen=10),  # últimas 10 alertas
    'last_alert_time': 0,
}

# Cargar modelo una sola vez (lazy: al primer request)
model = None
model_lock = threading.Lock()

def get_model():
    global model
    with model_lock:
        if model is None:
            print(f'Cargando modelo {MODEL_PATH}...')
            model = YOLO(MODEL_PATH)
            print(f'Modelo cargado. Clases: {model.names}')
        return model


def generate_frames():
    """Generador que produce frames procesados con detecciones."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f'ERROR: no se pudo abrir cámara índice {CAMERA_INDEX}')
        return

    model_instance = get_model()
    prev_time = time.time()
    fps_smoothed = 0
    frame_count = 0
    last_annotated = None
    last_n_detections = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Procesar 1 de cada N frames
        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            results = model_instance.predict(
                source=frame,
                conf=CONF_THRESHOLD,
                imgsz=INFERENCE_SIZE,
                verbose=False
            )
            last_annotated = results[0].plot()
            last_n_detections = len(results[0].boxes)

            # Registrar alerta si hay detección (rate-limited a 1 cada 2s)
            now = time.time()
            with state_lock:
                if last_n_detections > 0 and (now - state['last_alert_time']) > 2.0:
                    state['last_alert_time'] = now
                    state['total_detections_session'] += last_n_detections

                    # Tomar la confianza más alta de la detección
                    confs = [float(box.conf.item()) for box in results[0].boxes]
                    max_conf = max(confs) if confs else 0

                    alert = {
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'count': last_n_detections,
                        'confidence': round(max_conf * 100, 1)
                    }
                    state['alerts'].appendleft(alert)

        display_frame = last_annotated if last_annotated is not None else frame

        # FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if current_time != prev_time else 0
        fps_smoothed = 0.9 * fps_smoothed + 0.1 * fps
        prev_time = current_time

        with state_lock:
            state['fps'] = round(fps_smoothed, 1)
            state['detections'] = last_n_detections

        # Codificar como JPEG para streaming
        ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        frame_count += 1

    cap.release()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/stats')
def stats():
    """Endpoint JSON con métricas para que el frontend las consulte."""
    with state_lock:
        return jsonify({
            'fps': state['fps'],
            'detections': state['detections'],
            'total_session': state['total_detections_session'],
            'alerts': list(state['alerts']),
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })


if __name__ == '__main__':
    print('=' * 50)
    print('Demo Cigarro - Camara de Seguridad ATM')
    print('Abrir http://localhost:5000 en el navegador')
    print('Presionar Ctrl+C para salir')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
