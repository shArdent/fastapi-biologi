import numpy as np
import tensorflow as tf
import gdown

import os


def load_model(app, path: str):
    global env2
    global base_env2

    model = tf.keras.models.load_model(path, compile=False)

    if model is None:
        raise ValueError("Model gagal dimuat.")

    app.state.env2 = model
    base_env2 = model.layers[0]

    conv_layer_name = "top_conv"

    try:
        layer = base_env2.get_layer(conv_layer_name)
    except Exception as e:
        print(e)

    app.state.grad_model = tf.keras.models.Model(
        [base_env2.input], [layer.output, base_env2.output]
    )


def download_model(path: str):
    if not os.path.exists(path):
        os.makedirs("models", exist_ok=True)
        file_id = os.getenv("MODEL_FILE_ID")
        url = f"https://drive.google.com/uc?id={file_id}"
        tmp_path = path + ".part"
        gdown.download(url, output=tmp_path, quiet=False, fuzzy=True)

        if os.path.exists(tmp_path):
            os.rename(tmp_path, path)
    else:
        print("Model sudah ada")
