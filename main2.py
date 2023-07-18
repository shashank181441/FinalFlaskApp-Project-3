import cv2
import mediapipe as mp

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection()

from spoofDetect import util
from spoofDetect.test import test

cap = cv2.VideoCapture(1)
frames_to_analyze = 15
label_count = {0: 0, 1: 0}

while True:
    for _ in range(frames_to_analyze):
        ret, frame = cap.read()

        if not ret:
            break

        # Convert the frame to RGB for Mediapipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces using Mediapipe
        results = face_detection.process(frame_rgb)

        if results.detections:
            # Get the bounding box coordinates of the detected face
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * frame.shape[1])
                y = int(bbox.ymin * frame.shape[0])
                w = int(bbox.width * frame.shape[1])
                h = int(bbox.height * frame.shape[0])

                # Perform the spoof detection on the cropped face
                label = test(image=frame,
                             model_dir='/Users/shashankpandey/Downloads/spoofsss/spoofDetect/resources/anti_spoof_models',
                             device_id=0)

                # Check if the label is valid (0 or 1)
                if label in label_count:
                    # Update the label count dictionary
                    label_count[label] += 1

                    # Draw a bounding box around the face
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                    # Write the label value inside the bounding box
                    label_text = 'Real' if label == 1 else 'Fake'
                    cv2.putText(frame, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Display the video feed with bounding box
        cv2.imshow('Camera Feed', frame)

        # Check for 'q' key press to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Determine the majority label
    majority_label = max(label_count, key=label_count.get)

    # Print the result based on the majority label
    if majority_label == 1:
        print('Real')
    else:
        print('Fake')

    # Reset the label count dictionary
    label_count = {0: 0, 1: 0}

# Release the video capture object
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()
