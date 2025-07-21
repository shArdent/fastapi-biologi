import numpy as np
import tensorflow as tf
import gdown

import os


env2 = None
base_env2 = None


def load_model(path: str):
    global env2
    global base_env2
    env2 = tf.keras.models.load_model(path)
    base_env2 = env2.layers[0]


def download_model(path:str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        file_id = os.getenv("MODEL_FILE_ID")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, path, quiet=False)
    else:
        print("Model sudah ada")
