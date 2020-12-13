import numpy as np
import cv2
from object_detection.builders import model_builder
from object_detection.utils import visualization_utils as viz_utils
from object_detection.utils import config_util
from object_detection.utils import label_map_util
import tensorflow as tf
import tarfile
import urllib.request
import os
import tensorflow as tf
# tf.compat.v1.disable_eager_execution()
MODELS_DIR = 'exported-models/'
MODEL_NAME = 'my_model/'
# PATH_TO_MODEL_TAR = os.path.join(MODELS_DIR, MODEL_TAR_FILENAME)
PATH_TO_CKPT = os.path.join(
    MODELS_DIR, os.path.join(MODEL_NAME, 'checkpoint/'))
PATH_TO_CFG = os.path.join(
    MODELS_DIR, os.path.join(MODEL_NAME, 'pipeline.config'))
# if not os.path.exists(PATH_TO_CKPT):
#     print('Downloading model. This may take a while... ', end='')
#     urllib.request.urlretrieve(MODEL_DOWNLOAD_LINK, PATH_TO_MODEL_TAR)
#     tar_file = tarfile.open(PATH_TO_MODEL_TAR)
#     tar_file.extractall(MODELS_DIR)
#     tar_file.close()
#     os.remove(PATH_TO_MODEL_TAR)
#     print('Done')

# Download labels file
LABEL_FILENAME = 'label_map.pbtxt'
PATH_TO_LABELS = LABEL_FILENAME
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'    # Suppress TensorFlow logging

tf.get_logger().setLevel('ERROR')           # Suppress TensorFlow logging (2)

# Enable GPU dynamic memory allocation
gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

# Load pipeline config and build a detection model
configs = config_util.get_configs_from_pipeline_file(PATH_TO_CFG)
model_config = configs['model']
detection_model = model_builder.build(
    model_config=model_config, is_training=False)

# Restore checkpoint
ckpt = tf.compat.v2.train.Checkpoint(model=detection_model)
ckpt.restore(os.path.join(PATH_TO_CKPT, 'ckpt-0')).expect_partial()


@tf.function
def detect_fn(image):
    """Detect objects in image."""

    image, shapes = detection_model.preprocess(image)
    prediction_dict = detection_model.predict(image, shapes)
    detections = detection_model.postprocess(prediction_dict, shapes)

    return detections, prediction_dict, tf.reshape(shapes, [-1])


category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS,
                                                                    use_display_name=True)

cap = cv2.VideoCapture(0)

while True:
    # Read frame from camera
    ret, image_np = cap.read()

    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)

    # Things to try:
    # Flip horizontally
    # image_np = np.fliplr(image_np).copy()

    # Convert image to grayscale
    # image_np = np.tile(
    #     np.mean(image_np, 2, keepdims=True), (1, 1, 3)).astype(np.uint8)

    input_tensor = tf.convert_to_tensor(
        np.expand_dims(image_np, 0), dtype=tf.float32)
    detections, predictions_dict, shapes = detect_fn(input_tensor)

    gun_pd = detections['detection_scores'].numpy()[0][0]
    knife_pd = detections['detection_scores'].numpy()[0][1]
    print("gun:" + str(detections['detection_scores'].numpy()[0][1]))
    print("knife:" + str(detections['detection_scores'].numpy()[0][1]))

    import requests
    url = "http://localhost:5000/ai/"

    if(gun_pd > 0.55):
        requests.post(
            url + "cfh/", data={"email": "284363.Camera.849", "coords": {75, 22}})

    if(knife_pd > 0.4):
        requests.post(
            url+"warning/", data={"email": "284363.Camera.849", "coords": {75, 22}})

    label_id_offset = 1
    image_np_with_detections = image_np.copy()

    viz_utils.visualize_boxes_and_labels_on_image_array(
        image_np_with_detections,
        detections['detection_boxes'][0].numpy(),
        (detections['detection_classes']
         [0].numpy() + label_id_offset).astype(int),
        detections['detection_scores'][0].numpy(),
        category_index,
        use_normalized_coordinates=True,
        max_boxes_to_draw=200,
        min_score_thresh=.30,
        agnostic_mode=False)

    # Display output
    cv2.imshow('object detection', cv2.resize(
        image_np_with_detections, (800, 600)))
    # print([category_index.get(value)
    #        for index, value in enumerate(detections['detection_classes'][0]) if detections['detection_scores'][0, index] > 0.5])
    print([i for i in detections])

    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()