import tensorflow as tf
import numpy as np
import cv2


def get_gradcam_heatmap(mod, img_array, conv_layer_name, class_index=None):
    layer = mod.get_layer(conv_layer_name)
    grad_model = tf.keras.models.Model([mod.input], [layer.output, mod.output])
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        output_shape = conv_outputs.shape
        if len(output_shape) == 2:  # (batch, classes): logits/softmax layer
            if class_index is None:
                class_index = tf.argmax(predictions[0])
            num_classes = predictions.shape[1]
            if class_index >= num_classes:
                class_index = int(tf.argmax(predictions[0]))
            class_output = predictions[:, class_index]
            grads = tape.gradient(class_output, conv_outputs)[0]
        else:
            # class-agnostic Grad-CAM: mean of predictions
            pooled_output = tf.reduce_mean(predictions)
            grads = tape.gradient(pooled_output, conv_outputs)[0]
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1))
    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy()


def overlay_bounding_boxes(
    img_pil, heatmap, threshold=0.25, box_color=(0, 255, 0), box_width=3
):
    img = np.array(img_pil.resize((224, 224))).astype(np.uint8).copy()
    heatmap_resized = cv2.resize(heatmap, (img.shape[1], img.shape[0]))
    heatmap_blurred = cv2.GaussianBlur(heatmap_resized, (7, 7), 0)
    heatmap_scaled = (255 * heatmap_blurred).astype(np.uint8)
    _, binary_map = cv2.threshold(
        heatmap_scaled, int(threshold * 255), 255, cv2.THRESH_BINARY
    )
    contours, _ = cv2.findContours(
        binary_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(img, (x, y), (x + w, y + h), box_color, box_width)
    return img
