#!/usr/bin/env python3
"""
generar_video.py
──────────────────────────────────────────────────
Genera un video tipo noticiero con:
- Voz en español mexicano (edge-tts)
- Texto animado sobre fondo oscuro
- Secciones: macro, electoral, geopolítica

Uso:
    python3 generar_video.py

Requiere: edge-tts, moviepy, pillow
"""

import json
import os
import asyncio
import textwrap
from datetime import datetime
from pathlib import Path

FECHA    = datetime.now().strftime("%Y-%m-%d")
HORA     = datetime.now().strftime("%H:%M")
VOZ      = "es-MX-JorgeNeural"
TMP_DIR  = "/tmp/nicho_video"
SALIDA   = f"resumen_{FECHA}.mp4"

os.makedirs(TMP_DIR, exist_ok=True)

# ─────────────────────────────────────────
# LEER DATOS DEL PIPELINE
# ─────────────────────────────────────────
def leer_macro():
    path = f"datos_crudos/macro_mx_{FECHA}.jsonl"
    macro = {}
    if not os.path.exists(path):
        return macro
    with open(path, encoding="utf-8") as f:
        for linea in f:
            try:
                d = json.loads(linea)
                macro[d["titulo"]] = d.get("valor", "N/D")
            except Exception:
                pass
    return macro

def leer_candidatos():
    if not os.path.exists("candidatos.json"):
        return []
    with open("candidatos.json", encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data.get("candidatos", []), key=lambda c: c.get("score_compuesto", c.get("pct", 0)), reverse=True)

def leer_geopolitica():
    path = f"datos_filtrados/filtrado_{FECHA}.json"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("geopolitica", [])[:3]

# ─────────────────────────────────────────
# CONSTRUIR GUIÓN
# ─────────────────────────────────────────
def construir_guion():
    macro      = leer_macro()
    candidatos = leer_candidatos()
    geo        = leer_geopolitica()

    secciones = []

    # INTRO
    secciones.append({
        "titulo": f"NICHO ANALYZER\n{FECHA}",
        "texto_pantalla": f"NICHO ANALYZER\nResumen del día\n{FECHA}  {HORA}",
        "voz": f"Bienvenidos al resumen diario de Nicho Analyzer. Hoy es {FECHA.replace('-', ' de ')}. "
               f"A continuación, los principales indicadores económicos, el radar electoral de Zacatecas y las señales geopolíticas del día."
    })

    # MACRO
    mxn   = macro.get("USD/MXN Tipo de cambio FIX", "N/D")
    infl  = macro.get("Inflacion INPC anual Mexico", "N/D")
    tasa  = macro.get("Tasa objetivo Banxico", "N/D")
    wti   = macro.get("WTI", "N/D")

    secciones.append({
        "titulo": "ECONOMÍA MÉXICO",
        "texto_pantalla": f"ECONOMÍA MÉXICO\n\nDólar: ${mxn} MXN\nInflación: {infl}%\nTasa Banxico: {tasa}%\nPetróleo WTI: ${wti} USD",
        "voz": f"En economía. El tipo de cambio del dólar se ubica en {mxn} pesos. "
               f"La inflación anual es de {infl} por ciento. "
               f"La tasa de referencia del Banco de México permanece en {tasa} por ciento. "
               f"El petróleo WTI cotiza en {wti} dólares por barril."
    })

    # ELECTORAL
    if candidatos:
        top3 = candidatos[:3]
        texto_pantalla = "RADAR ELECTORAL\nZACATECAS 2027\n\n"
        voz_electoral = "En el radar electoral de Zacatecas 2027. "

        for i, c in enumerate(top3):
            medal = ["Primero", "Segundo", "Tercero"][i]
            score = c.get("score_compuesto", c.get("pct", 0))
            texto_pantalla += f"{i+1}. {c['nombre']} ({c['partido']}) {score}%\n"
            voz_electoral += (
                f"En {medal} lugar, {c['nombre']} del {c['partido']}, "
                f"con un índice de {score} por ciento. "
            )

        voz_electoral += "Estos datos combinan encuestas de intención de voto y presencia digital en medios."

        secciones.append({
            "titulo": "RADAR ELECTORAL ZACATECAS",
            "texto_pantalla": texto_pantalla.strip(),
            "voz": voz_electoral
        })

    # GEOPOLÍTICA
    if geo:
        texto_pantalla = "SEÑALES GEOPOLÍTICAS\n\n"
        voz_geo = "En el panorama geopolítico internacional. "

        for e in geo[:3]:
            titulo = e.get("titulo", "")[:80]
            texto_pantalla += f"▸ {titulo}\n"
            voz_geo += f"{titulo}. "

        secciones.append({
            "titulo": "SEÑALES GEOPOLÍTICAS",
            "texto_pantalla": texto_pantalla.strip(),
            "voz": voz_geo
        })

    # CIERRE
    secciones.append({
        "titulo": "NICHO ANALYZER",
        "texto_pantalla": "NICHO ANALYZER\nruskigarage-alt.github.io\n/nicho-analyzer\n\nActualización diaria",
        "voz": "Esto ha sido el resumen diario de Nicho Analyzer. "
               "Para más información, visita nuestro sitio web. Hasta mañana."
    })

    return secciones

# ─────────────────────────────────────────
# GENERAR AUDIO CON EDGE-TTS
# ─────────────────────────────────────────
async def generar_audio(texto, ruta_salida):
    import edge_tts
    communicate = edge_tts.Communicate(texto, VOZ, rate="+5%")
    await communicate.save(ruta_salida)

# ─────────────────────────────────────────
# GENERAR FRAME DE VIDEO (imagen)
# ─────────────────────────────────────────
def generar_frame(texto, ruta_salida, w=1280, h=720):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (w, h), color=(8, 9, 12))
    draw = ImageDraw.Draw(img)

    # Línea decorativa superior
    draw.rectangle([0, 0, w, 4], fill=(0, 212, 255))

    # Línea decorativa inferior
    draw.rectangle([0, h-4, w, h], fill=(0, 212, 255))

    # Logo esquina superior izquierda
    draw.text((24, 16), "◈ NICHO ANALYZER", fill=(0, 212, 255),
              font=None)

    # Fecha esquina superior derecha
    draw.text((w-200, 16), FECHA, fill=(74, 158, 255), font=None)

    # Texto principal centrado
    lineas = texto.split("\n")
    y_start = h // 2 - (len(lineas) * 28) // 2

    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea:
            continue

        # Primera línea = título grande
        if i == 0:
            color = (224, 244, 255)
            size_factor = 2
        elif linea.startswith("▸"):
            color = (176, 216, 232)
            size_factor = 1
        elif any(c.isdigit() for c in linea[:3]):
            color = (99, 102, 241)
            size_factor = 1
        else:
            color = (107, 114, 128)
            size_factor = 1

        # Centrar texto
        bbox = draw.textbbox((0, 0), linea)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2

        draw.text((x, y_start + i * 36), linea, fill=color)

    # Línea separadora
    draw.rectangle([60, y_start - 20, w-60, y_start - 18], fill=(30, 33, 48))

    img.save(ruta_salida)

# ─────────────────────────────────────────
# ENSAMBLAR VIDEO
# ─────────────────────────────────────────
def ensamblar_video(clips_data):
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

    clips = []
    for i, (imagen_path, audio_path) in enumerate(clips_data):
        try:
            audio = AudioFileClip(audio_path)
            duracion = audio.duration + 0.5  # pequeña pausa al final

            clip = ImageClip(imagen_path, duration=duracion)
            clip = clip.with_audio(audio)
            clips.append(clip)
            print(f"  ✓ Clip {i+1}: {duracion:.1f}s")
        except Exception as e:
            print(f"  ✗ Error en clip {i+1}: {e}")

    if not clips:
        print("✗ No se generaron clips")
        return False

    video_final = concatenate_videoclips(clips, method="compose")
    video_final.write_videofile(
        SALIDA,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )
    return True

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
async def main_async():
    print(f"\n=== GENERANDO VIDEO — {FECHA} ===")

    secciones = construir_guion()
    print(f"  Secciones: {len(secciones)}")

    clips_data = []

    for i, seccion in enumerate(secciones):
        print(f"\n[ {i+1}/{len(secciones)} ] {seccion['titulo']}")

        # Generar imagen
        img_path = f"{TMP_DIR}/frame_{i:02d}.png"
        generar_frame(seccion["texto_pantalla"], img_path)
        print(f"  ✓ Frame generado")

        # Generar audio
        audio_path = f"{TMP_DIR}/audio_{i:02d}.mp3"
        await generar_audio(seccion["voz"], audio_path)
        duracion = os.path.getsize(audio_path) / 1024
        print(f"  ✓ Audio generado ({duracion:.0f} KB)")

        clips_data.append((img_path, audio_path))

    print(f"\n[ ENSAMBLANDO VIDEO ]")
    ok = ensamblar_video(clips_data)

    if ok:
        size_mb = os.path.getsize(SALIDA) / (1024*1024)
        print(f"\n✓ Video generado: {SALIDA} ({size_mb:.1f} MB)")
        print(f"  Listo para compartir en Telegram o WhatsApp")
    else:
        print("\n✗ Error al ensamblar video")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
