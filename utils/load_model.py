import tensorflow as tf
import numpy as np
from tensorflow.keras.models import load_model


env2 = load_model("models/env2.h5")

base_env2 = env2.layers[0]
