from constants.labels import plant_translate


def decode_prediction(predicted_class):
    if "___" in predicted_class:
        plant_raw, disease_raw = predicted_class.split("___", 1)
    else:
        plant_raw, disease_raw = predicted_class, "Unknown"

    plant_name = plant_raw.replace("_", " ")
    is_healthy = "healthy" in disease_raw.lower()
    disease_name = disease_raw.replace("_", " ") if not is_healthy else "Sehat"

    key = plant_name.replace("(", "").replace(")", "").replace(",", "").strip()
    plant_final = plant_translate.get(key, key.lower())

    if is_healthy:
        readable = f"Tanaman {plant_final} ini sehat."
    else:
        readable = (
            f"Tanaman {plant_final} ini memiliki penyakit {disease_name.lower()}."
        )

    return plant_final, disease_name, is_healthy, readable
