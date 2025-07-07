import numpy as np
from PIL import Image
from keras.applications.efficientnet_v2 import preprocess_input

def preprocess_image(image: Image.Image):
    image = image.resize((224, 224))
    img_array = np.array(image)
    img_array = preprocess_input(img_array)
    return np.expand_dims(img_array, axis=0)