import streamlit as st
import tensorflow as tf
import numpy as np
from PIL import Image
import sqlite3
import os
from datetime import datetime, timedelta
import uuid

# =========================================================
# EINSTELLUNGEN
# =========================================================

DB_NAME = "fundkiste.db"
IMAGE_FOLDER = "images"
MODEL_PATH = "keras_model.h5"

CLASS_NAMES = ["Rucksack", "Jacke", "Flasche"]

# =========================================================
# ORDNER ERSTELLEN (falls nicht vorhanden)
# =========================================================

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# =========================================================
# DATENBANK VERBINDUNG
# =========================================================

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# Tabelle erstellen
c.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT,
    klasse TEXT,
    wahrscheinlichkeit REAL,
    farbe TEXT,
    groesse TEXT,
    zeitstempel TEXT,
    status TEXT
)
""")
conn.commit()

# =========================================================
# ALTE EINTRÄGE LÖSCHEN (älter als 2 Tage & Status Abgeholt)
# =========================================================

def delete_old_entries():
    two_days_ago = datetime.now() - timedelta(days=2)

    c.execute("SELECT id, image_path, zeitstempel FROM items WHERE status = 'Abgeholt'")
    rows = c.fetchall()

    for row in rows:
        item_id, image_path, zeit = row
        zeit_obj = datetime.fromisoformat(zeit)

        if zeit_obj < two_days_ago:
            # Bild löschen
            if os.path.exists(image_path):
                os.remove(image_path)

            # DB Eintrag löschen
            c.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()

delete_old_entries()

# =========================================================
# MODELL LADEN
# =========================================================

@st.cache_resource
def load_model():
    return tf.keras.models.load_model(MODEL_PATH)

model = load_model()

# =========================================================
# STREAMLIT UI
# =========================================================

st.title("🏫 Schul-Fundkiste")

menu = st.sidebar.radio("Menü", ["Neues Fundstück", "Übersicht"])

# =========================================================
# 1️⃣ NEUES FUNDSTÜCK
# =========================================================

if menu == "Neues Fundstück":

    st.header("Neues Fundstück hinzufügen")

    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])

    if uploaded_file is not None:

        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Hochgeladenes Bild", width=300)

        # Bild vorbereiten für Modell (224x224 für Teachable Machine)
        img = image.resize((224, 224))
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = model.predict(img_array)
        predicted_index = np.argmax(prediction)
        predicted_class = CLASS_NAMES[predicted_index]
        confidence = float(np.max(prediction)) * 100

        st.success(f"Erkannt: {predicted_class}")
        st.info(f"Wahrscheinlichkeit: {confidence:.2f}%")

        farbe = st.text_input("Farbe")
        groesse = st.text_input("Größe")

        if st.button("Speichern"):

            # Bild speichern
            filename = f"{uuid.uuid4()}.jpg"
            image_path = os.path.join(IMAGE_FOLDER, filename)
            image.save(image_path)

            # In DB speichern
            c.execute("""
                INSERT INTO items 
                (image_path, klasse, wahrscheinlichkeit, farbe, groesse, zeitstempel, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                image_path,
                predicted_class,
                confidence,
                farbe,
                groesse,
                datetime.now().isoformat(),
                "Neu gefunden"
            ))
            conn.commit()

            st.success("Fundstück gespeichert!")

# =========================================================
# 2️⃣ ÜBERSICHT
# =========================================================

elif menu == "Übersicht":

    st.header("Alle Fundstücke")

    # Suchfunktion
    st.subheader("🔍 Suche")

    search_class = st.selectbox("Klasse", ["Alle"] + CLASS_NAMES)
    search_color = st.text_input("Farbe suchen")
    search_size = st.text_input("Größe suchen")

    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if search_class != "Alle":
        query += " AND klasse = ?"
        params.append(search_class)

    if search_color:
        query += " AND farbe LIKE ?"
        params.append(f"%{search_color}%")

    if search_size:
        query += " AND groesse LIKE ?"
        params.append(f"%{search_size}%")

    c.execute(query, params)
    items = c.fetchall()

    neu = [item for item in items if item[7] == "Neu gefunden"]
    abgeholt = [item for item in items if item[7] == "Abgeholt"]

    # ==========================
    # Neu gefunden
    # ==========================

    st.subheader("🟢 Neu gefunden")

    for item in neu:
        with st.container():
            st.image(item[1], width=200)
            st.write(f"Klasse: {item[2]}")
            st.write(f"Wahrscheinlichkeit: {item[3]:.2f}%")
            st.write(f"Farbe: {item[4]}")
            st.write(f"Größe: {item[5]}")
            st.write(f"Gefunden am: {item[6]}")

            if st.button("Das ist meins", key=f"btn_{item[0]}"):
                c.execute("UPDATE items SET status = 'Abgeholt' WHERE id = ?", (item[0],))
                conn.commit()
                st.success("Als abgeholt markiert")
                st.rerun()

    # ==========================
    # Abgeholt
    # ==========================

    st.subheader("🟡 Abgeholt (wird in 2 Tagen gelöscht)")

    for item in abgeholt:
        with st.container():
            st.image(item[1], width=200)
            st.write(f"Klasse: {item[2]}")
            st.write(f"Farbe: {item[4]}")
            st.write(f"Größe: {item[5]}")
            st.write(f"Abgeholt am: {item[6]}")
