import os
import cv2
import numpy as np
import argparse
import warnings
import time

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name

warnings.filterwarnings('ignore')

# Initialize webcam
cap = cv2.VideoCapture(0)  # Use 0 for default webcam, or provide the video device index if multiple webcams are available

# Load anti-spoofing model
model_dir = "./resources/anti_spoof_models"  # Path to the anti-spoofing models
device_id = 0  # GPU device ID (if using GPU)
model_test = AntiSpoofPredict(device_id)
image_cropper = CropImage()

def check_image(image):
    height, width, channel = image.shape
    if width/height != 3/4:
        print("Image is not appropriate!!!\nHeight/Width should be 4/3.")
        return False
    else:
        return True

while True:
    # Capture frame from webcam
    ret, frame = cap.read()

    # Perform face detection using your preferred method
    # ...
    # Assuming you have obtained the face bounding box as (x, y, w, h)

    # Preprocess the face image if needed
    # ...
    
    # Check if the frame is read successfully
    if not ret:
        break
    
    # Perform spoof detection on the face image
    result = check_image(frame)
    if result is False:
        continue
    
    image_bbox = model_test.get_bbox(frame)
    prediction = np.zeros((1, 3))
    test_speed = 0
    # Sum the prediction from single model's result
    for model_name in os.listdir(model_dir):
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": frame,
            "bbox": image_bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False
        img = image_cropper.crop(**param)
        start = time.time()
        prediction += model_test.predict(img, os.path.join(model_dir, model_name))
        test_speed += time.time()-start

    # Draw result of prediction
    label = np.argmax(prediction)
    value = prediction[0][label]/2
    if label == 1:
        print("Real Face Detected. Score: {:.2f}.".format(value))
        result_text = "Real Face Score: {:.2f}".format(value)
        color = (255, 0, 0)
    else:
        print("Fake Face Detected. Score: {:.2f}.".format(value))
        result_text = "Fake Face Score: {:.2f}".format(value)
        color = (0, 0, 255)
    print("Prediction took {:.2f} s".format(test_speed))
    cv2.rectangle(
        frame,
        (image_bbox[0], image_bbox[1]),
        (image_bbox[0] + image_bbox[2], image_bbox[1] + image_bbox[3]),
        color, 2)
    cv2.putText(
        frame,
        result_text,
        (image_bbox[0], image_bbox[1] - 5),
        cv2.FONT_HERSHEY_COMPLEX, 0.5*frame.shape[0]/1024, color)

    # Display the frame with results
    cv2.imshow('Webcam', frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close any remaining OpenCV windows
cap.release()
cv2.destroyAllWindows()
