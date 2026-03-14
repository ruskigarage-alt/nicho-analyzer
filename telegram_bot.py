#!/usr/bin/env python3
"""
telegram_bot.py
──────────────────────────────────────────────────
Publica resumen diario en canal de Telegram.
Lee datos del pipeline y genera mensajes formateados.

Uso:
    python3 telegram_bot.py

Agregar a actualizar.sh al final, antes del git push:
    python3 telegram_bot.py
"""

import json
import os
import requests
from datetime import datetime

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
TOKEN   = "8503744013:AAGypL-4K_M24SqMnTc7ERWibG6RKKe73f8"
CANAL   = "@finanzas_zac"
FECHA   = datetime.now().strftime("%Y-%m-%d")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# ─────────────────────────────────────────
# ENVIAR MENSAJE
# ─────────────────────────────────────────
def enviar(texto, parse_mode="HTML"):
    try:
        r = requests.post(f"{API_URL}/sendMessage", json={
            "chat_id":    CANAL,
            "text":       texto,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }, timeout=15)
        if r.status_code == 200:
            print(f"  ✓ Mensaje enviado ({len(texto)} chars)")
            return True
        else:
            print(f"  ✗ Error Telegram: {r.status_code} — {r.text[:100]}")
            return False
    except Exception as e:
        print(f"  ✗ Error enviando: {e}")
        return False

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

def leer_electoral():
    path = f"datos_crudos/electoral_{FECHA}.json"
    if not os.path.exists(path):
        return {}, []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    momentum = data.get("momentum", {})
    entradas = data.get("entradas", [])
    return momentum, entradas

def leer_geopolitica():
    path = f"datos_filtrados/filtrado_{FECHA}.json"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("geopolitica", [])[:5]

def leer_economia():
    path = f"datos_filtrados/filtrado_{FECHA}.json"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("regulaciones_pyme", [])[:5]

def leer_candidatos():
    if not os.path.exists("candidatos.json"):
        return []
    with open("candidatos.json", encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data.get("candidatos", []), key=lambda c: c.get("pct", 0), reverse=True)

# ─────────────────────────────────────────
# CONSTRUIR MENSAJES
# ─────────────────────────────────────────
def msg_macro(macro):
    mxn   = macro.get("USD/MXN Tipo de cambio FIX", "N/D")
    infl  = macro.get("Inflacion INPC anual Mexico", "N/D")
    tasa  = macro.get("Tasa objetivo Banxico", "N/D")
    res   = macro.get("Reservas internacionales Banxico", "N/D")
    embi  = macro.get("Riesgo pais EMBI Mexico aproximado", "N/D")
    conf  = macro.get("Indice confianza macro Mexico", "N/D")
    wti   = macro.get("WTI", "N/D")
    brent = macro.get("Brent", "N/D")

    return f"""📊 <b>MACRO MÉXICO — {FECHA}</b>

💵 <b>Tipo de cambio:</b> ${mxn} MXN/USD
📈 <b>Inflación INPC:</b> {infl}%
🏦 <b>Tasa Banxico:</b> {tasa}%
🏛 <b>Reservas:</b> {res} mmd
⚠️ <b>Riesgo país EMBI:</b> {embi} pb
🎯 <b>Confianza macro:</b> {conf}/100

🛢 <b>Petróleo WTI:</b> ${wti} USD
🛢 <b>Brent:</b> ${brent} USD

🔗 <a href="https://ruskigarage-alt.github.io/nicho-analyzer/dashboard.html">Ver dashboard completo</a>"""

def msg_electoral(candidatos, momentum):
    if not candidatos:
        return None

    lineas = [f"🗳 <b>RADAR ELECTORAL ZACATECAS 2027 — {FECHA}</b>\n"]

    for i, c in enumerate(candidatos[:5]):
        medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][i]
        nombre  = c.get("nombre", "")
        partido = c.get("partido", "")
        pct     = c.get("pct", 0)
        menciones = c.get("menciones", 0)
        mom     = c.get("momentum", 0)
        mom_str = f"+{mom}" if mom >= 0 else str(mom)
        mom_icon = "📈" if mom > 0 else ("📉" if mom < 0 else "➡️")

        lineas.append(
            f"{medal} <b>{nombre}</b> ({partido})\n"
            f"   Encuesta: {pct}% | Menciones: {menciones} | Momentum: {mom_icon} {mom_str}"
        )

    lineas.append(f"\n🔗 <a href=\"https://ruskigarage-alt.github.io/nicho-analyzer/scoreboard.html\">Ver scoreboard electoral</a>")
    return "\n".join(lineas)

def msg_geopolitica(entradas):
    if not entradas:
        return None

    lineas = [f"🌍 <b>SEÑALES GEOPOLÍTICAS — {FECHA}</b>\n"]
    for e in entradas[:4]:
        titulo = e.get("titulo", "")[:100]
        fuente = e.get("fuente_nombre", e.get("fuente", "")).replace("_", " ")
        lineas.append(f"▸ {titulo}\n  <i>{fuente}</i>")

    lineas.append(f"\n🔗 <a href=\"https://ruskigarage-alt.github.io/nicho-analyzer/radar_geopolitico.html\">Ver radar geopolítico</a>")
    return "\n".join(lineas)

def msg_economia(entradas):
    if not entradas:
        return None

    lineas = [f"💼 <b>ECONOMÍA Y REGULACIONES — {FECHA}</b>\n"]
    for e in entradas[:4]:
        titulo = e.get("titulo", "")[:100]
        fuente = e.get("fuente_nombre", e.get("fuente", "")).replace("_", " ")
        lineas.append(f"▸ {titulo}\n  <i>{fuente}</i>")

    lineas.append(f"\n🔗 <a href=\"https://ruskigarage-alt.github.io/nicho-analyzer/dashboard.html\">Ver dashboard</a>")
    return "\n".join(lineas)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(f"\n=== TELEGRAM BOT — {FECHA} ===")

    # Verificar conexión con Telegram
    r = requests.get(f"{API_URL}/getMe", timeout=10)
    if r.status_code != 200:
        print(f"✗ No se pudo conectar con Telegram: {r.text[:100]}")
        return
    bot_name = r.json().get("result", {}).get("username", "desconocido")
    print(f"  Bot conectado: @{bot_name}")

    # Leer datos
    macro      = leer_macro()
    candidatos = leer_candidatos()
    momentum, entradas_electorales = leer_electoral()
    geo        = leer_geopolitica()
    eco        = leer_economia()

    # Enviar mensajes con pausa entre cada uno
    import time

    print("\n[ 1/4 ] Macro México...")
    m1 = msg_macro(macro)
    enviar(m1)
    time.sleep(2)

    print("[ 2/4 ] Electoral Zacatecas...")
    m2 = msg_electoral(candidatos, momentum)
    if m2:
        enviar(m2)
        time.sleep(2)

    print("[ 3/4 ] Geopolítica...")
    m3 = msg_geopolitica(geo)
    if m3:
        enviar(m3)
        time.sleep(2)

    print("[ 4/4 ] Economía...")
    m4 = msg_economia(eco)
    if m4:
        enviar(m4)

    print(f"\n✓ Resumen publicado en {CANAL}")

if __name__ == "__main__":
    main()
