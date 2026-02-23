import streamlit as st
import tensorflow as tf
from PIL import Image
import numpy as np
import os

# ---------------------------------
# Modell laden
# ---------------------------------
MODEL_PATH = "keras_model.h5"

@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Modell {MODEL_PATH} nicht gefunden!")
        st.stop()
    return tf.keras.models.load_model(MODEL_PATH)

model = load_model()
