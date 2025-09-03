from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash, send_file
import mysql.connector
import cv2
import numpy as np
import face_recognition
import base64
import json
import os
import pytz
from datetime import datetime, date
from pathlib import Path
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'

db_config = {
    "host": "turntable.proxy.rlwy.net",
    "user": "root",
    "password": "MFezbJNQdUFOqpXsUjuENWzVihqMhHcK",
    "database": "railway",
    "port": 39807
}

def get_db_connection():
    conn = mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=db_config["port"],
        charset='utf8mb4',
        use_unicode=True
    )
    conn.set_charset_collation('utf8mb4')
    return conn

# Crear carpetas si no existen
Path("fotos/entrada").mkdir(parents=True, exist_ok=True)
Path("fotos/salida").mkdir(parents=True, exist_ok=True)

# Zona horaria local (CDMX)
tz = pytz.timezone('America/Mexico_City')

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'Tromluc_registros2025':
            return redirect(url_for('registro'))
        elif password == 'admin2':
            return redirect(url_for('asistencia_html'))
        else:
            return render_template('index.html', error="❌ Contraseña incorrecta.")
    return render_template('index.html')

# ---------------- REGISTRO ----------------
@app.route('/registro')
def registro():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_tipo, tipo_usuario FROM tipo_usuario")
    tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('registro.html', tipos=tipos)

# ---------------- REGISTRAR PERSONA ----------------
@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    apellido_paterno = request.form['apellido_paterno']
    apellido_materno = request.form['apellido_materno']
    id_tipo = request.form['tipo_usuario']
    foto_base64 = request.form['foto']

    if ',' in foto_base64:
        foto_base64 = foto_base64.split(',')[1]
    imagen_bytes = base64.b64decode(foto_base64)
    nparr = np.frombuffer(imagen_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    img = cv2.resize(img, (800, 600))
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    rostros = face_recognition.face_encodings(rgb_img)
    if len(rostros) == 0:
        for angle in [90, 180, 270]:
            rotated = cv2.rotate(rgb_img, {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }[angle])
            rostros = face_recognition.face_encodings(rotated)
            if len(rostros) > 0:
                rgb_img = rotated
                break
    if len(rostros) == 0:
        espejada = cv2.flip(rgb_img, 1)
        rostros = face_recognition.face_encodings(espejada)
        if len(rostros) > 0:
            rgb_img = espejada

    if len(rostros) == 0:
        flash("❌ No se detectó rostro. Asegúrate de estar bien iluminado, de frente y no tan cerca del celular.", "error")
        return redirect(url_for('registro'))

    vector_rostro = json.dumps(rostros[0].tolist())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
         INSERT INTO emp_activos (vectores_rostro, nombre, apellido_pa, apellido_ma, id_tipo)
         VALUES (%s, %s, %s, %s, %s)
         ''', (vector_rostro, nombre, apellido_paterno, apellido_materno, id_tipo))
        conn.commit()
        cursor.close()
        conn.close()
        flash("✅ Usuario registrado correctamente", "success")
    except Exception as e:
        flash(f"❌ Error al guardar: {e}", "error")

    return redirect(url_for('registro'))

# ---------------- ASISTENCIA ----------------
@app.route('/asistencia')
def asistencia_html():
    return render_template('asistencia.html')

@app.route('/registrar_asistencia', methods=['POST'])
def registrar_asistencia():
    try:
        data = request.get_json()
        foto_base64 = data['foto']
        latitud = data.get('latitud')
        longitud = data.get('longitud')

        if ',' in foto_base64:
            foto_base64 = foto_base64.split(',')[1]
        imagen_bytes = base64.b64decode(foto_base64)
        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        img = cv2.resize(img, (800, 600))
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        rostros = face_recognition.face_encodings(rgb)
        if len(rostros) == 0:
            for angle in [90, 180, 270]:
                rotated = cv2.rotate(rgb, {
                    90: cv2.ROTATE_90_CLOCKWISE,
                    180: cv2.ROTATE_180,
                    270: cv2.ROTATE_90_COUNTERCLOCKWISE
                }[angle])
                rostros = face_recognition.face_encodings(rotated)
                if len(rostros) > 0:
                    rgb = rotated
                    break

        if len(rostros) == 0:
            espejada = cv2.flip(rgb, 1)
            rostros = face_recognition.face_encodings(espejada)
            if len(rostros) > 0:
                rgb = espejada

        if len(rostros) == 0:
            return jsonify({'status': 'fail', 'message': '❌ No se detectó rostro. Asegúrate de estar bien iluminado, de frente, y no muy cerca de la cámara.'})

        vector_nuevo = rostros[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_emp, vectores_rostro, nombre, apellido_pa FROM emp_activos")
        usuarios = cursor.fetchall()

        matches = []
        for codigo, vector_json, nombre, apellido in usuarios:
            vector_bd = np.array(json.loads(vector_json))
            distancia = face_recognition.face_distance([vector_bd], vector_nuevo)[0]
            if distancia < 0.5:
                matches.append((codigo, nombre, apellido, distancia))

        if not matches:
            cursor.close()
            conn.close()
            return jsonify({'status': 'fail', 'message': '❌ Rostro no reconocido'})

        matches.sort(key=lambda x: x[3])
        codigo_emp, nombre, apellido, _ = matches[0]
        hoy = datetime.now(tz).date()
        hora_actual = datetime.now(tz).time()

        cursor.execute("SELECT id_asistencia FROM asistencia WHERE fecha = %s AND codigo_emp = %s", (hoy, codigo_emp))
        registro = cursor.fetchone()

        nombre_archivo = f"{nombre}_{apellido}_{hoy.strftime('%Y%m%d')}.jpg"

        # ✅ VALIDACIÓN DE UBICACIONES SEPARADAS
        lat = float(latitud)
        lon = float(longitud)

        # Zona AIRES
        lat_min_aires = 20.6110
        lat_max_aires = 20.6127
        lon_min_aires = -101.2372
        lon_max_aires = -101.2357

        # Zona PINTURA
        lat_min_pintura = 20.6090
        lat_max_pintura = 20.6110
        lon_min_pintura = -101.2400
        lon_max_pintura = -101.2375

        if lat_min_aires <= lat <= lat_max_aires and lon_min_aires <= lon <= lon_max_aires:
            ubicacion = "Ubicación en zona de AIRES"
        elif lat_min_pintura <= lat <= lat_max_pintura and lon_min_pintura <= lon <= lon_max_pintura:
            ubicacion = "Ubicación en zona de PINTURA"
        else:
            ubicacion = "Ubicación fuera de la zona de trabajo"

        if registro:
            carpeta = "fotos/salida"
            ruta = os.path.join(carpeta, nombre_archivo)
            cv2.imwrite(ruta, img)

            cursor.execute("UPDATE asistencia SET hora_salida = %s, ubicacion = %s WHERE id_asistencia = %s", (hora_actual, ubicacion, registro[0]))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'status': 'ok', 'message': f'🕒 Salida registrada de {nombre}'})
        else:
            carpeta = "fotos/entrada"
            ruta = os.path.join(carpeta, nombre_archivo)
            cv2.imwrite(ruta, img)

            cursor.execute("""
                INSERT INTO asistencia (codigo_emp, vector, fecha, hora_entrada, latitud, longitud, ubicacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (codigo_emp, json.dumps(vector_nuevo.tolist()), hoy, hora_actual, latitud, longitud, ubicacion))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'status': 'ok', 'message': f'🕐 Entrada registrada de {nombre}'})

    except Exception as e:
        return jsonify({'status': 'fail', 'message': f'❌ Error: {str(e)}'})

# ---------------- REGISTROS ----------------
@app.route('/registros')
def mostrar_registros():
    fecha = request.args.get('fecha')
    conn = get_db_connection()
    cursor = conn.cursor()

    if fecha:
        cursor.execute("""
            SELECT e.codigo_emp, e.nombre, e.apellido_pa, e.apellido_ma, 
                   a.ubicacion, a.vector, a.fecha, a.hora_entrada, a.hora_salida
            FROM asistencia a
            JOIN emp_activos e ON a.codigo_emp = e.codigo_emp
            WHERE a.fecha = %s
            ORDER BY a.fecha DESC, a.hora_entrada ASC
        """, (fecha,))
    else:
        cursor.execute("""
            SELECT e.codigo_emp, e.nombre, e.apellido_pa, e.apellido_ma, 
                   a.ubicacion, a.vector, a.fecha, a.hora_entrada, a.hora_salida
            FROM asistencia a
            JOIN emp_activos e ON a.codigo_emp = e.codigo_emp
            ORDER BY a.fecha DESC, a.hora_entrada ASC
        """)

    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('registros.html', registros=registros)

# ---------------- DESCARGAR EXCEL ----------------
@app.route('/descargar_excel')
def descargar_excel():
    try:
        fecha = request.args.get('fecha')
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT 
                e.codigo_emp, 
                e.nombre, 
                e.apellido_pa, 
                e.apellido_ma, 
                a.ubicacion, 
                a.fecha, 
                a.hora_entrada, 
                a.hora_salida
            FROM emp_activos e
            JOIN asistencia a ON e.codigo_emp = a.codigo_emp
        '''
        params = ()
        if fecha:
            query += " WHERE a.fecha = %s"
            params = (fecha,)

        cursor.execute(query, params)
        registros = cursor.fetchall()
        cursor.close()
        conn.close()

        columnas = [
            'Código Empleado',
            'Nombre',
            'Apellido Paterno',
            'Apellido Materno',
            'Ubicación',
            'Fecha',
            'Hora Entrada',
            'Hora Salida'
        ]
        df = pd.DataFrame(registros, columns=columnas)

        def format_timedelta(td):
            if pd.isnull(td):
                return ''
            total_seconds = int(td.total_seconds())
            horas = total_seconds // 3600
            minutos = (total_seconds % 3600) // 60
            segundos = total_seconds % 60
            return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

        df['Hora Entrada'] = df['Hora Entrada'].apply(format_timedelta)
        df['Hora Salida'] = df['Hora Salida'].apply(format_timedelta)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Asistencia')
        output.seek(0)

        return send_file(
            output,
            download_name='registros_asistencia.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return f"❌ Error al generar Excel: {str(e)}"

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    pass
    # app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
