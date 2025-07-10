import numpy as np
from keras.applications.efficientnet_v2 import preprocess_input


def preprocess_image(image):
    image = image.resize((224, 224))
    img_array = np.array(image).astype(np.float32)
    img_array = preprocess_input(img_array)
    return np.expand_dims(img_array, axis=0)
