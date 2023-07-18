from collections import Counter
import csv
import datetime
import io
import face_recognition
from flask import Flask, render_template, request, redirect, url_for, Response, session
import cv2
import os
import numpy as np
import redis
from insightface.app import FaceAnalysis
import face_rec
# app = Flask(__name__)

# Configure Redis connection
hostname = 'redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com'
portnumber = 12084
password = 'HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd'

r = redis.StrictRedis(host=hostname, port=portnumber, password=password)

# Configure face analysis model
faceapp = FaceAnalysis(name='buffalo_sc', root='insightface_model', providers=['CPUExecutionProvider'])
faceapp.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)

unique_values=[]


def generate_frames():
    cap = cv2.VideoCapture(0)  # 0 for default camera, 1 for external camera

    while True:
        ret, frame = cap.read()

        if not ret:
            break
        try:
            pred_frame, names, total_counts = face_rec.face_predictionss(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)
            # print(face_rec.face_prediction(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5))
            for name, role in names:
                if name and name !='Unknown':
                    if total_counts[name]["Real"]+total_counts[name]["Fake"]>=10:
                        if total_counts[name]["Real"]>total_counts[name]["Fake"]:
                            print(name)
                            print(unique_values)
                            value = name
                            if not value:
                                break

                            # Generate the unique value with datetime
                            unique_value = f"{value}@{role}@{datetime.datetime.now()}"
                            # Extract the value without datetime for comparison
                            extracted_value = value.split("@")[0]
                            # Check if the extracted value is already present in the list
                            if extracted_value not in [val.split("@")[0] for val in unique_values]:
                                unique_values.append(unique_value)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            continue
        
        ret, buffer = cv2.imencode('.jpg', pred_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

def capture_photos(person_name, role):
    key = person_name + '@' + role
    if key in r.hkeys("academy:register"):
        print(f"Warning: {person_name} has already been trained. Skipping training...")
        return ''
    cap = cv2.VideoCapture(1)  # 0 for default camera, 1 for external camera
    face_embeddings = []
    sample = 0

    while sample < 50:
        ret, frame = cap.read()
        if not ret:
            print('Unable to read camera')
            break

        # Get results from insightface model
        results = faceapp.get(frame, max_num=1)
        for res in results:
            sample += 1
            x1, y1, x2, y2 = res['bbox'].astype(int)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

            # Facial features
            embeddings = res['embedding']
            face_embeddings.append(embeddings)

        img_filename = f'{key}_{sample}.jpg'
        cv2.imwrite(os.path.join('static', img_filename), frame)

        if sample == 50:
            break

    cap.release()

    # Calculate mean facial embedding
    if len(face_embeddings) > 0:
        x_mean = np.mean(face_embeddings, axis=0)
        x_mean_bytes = x_mean.tobytes()

        # Save data into Redis
        r.hset(name='academy:register', key=key, value=x_mean_bytes)

        # Delete captured images
        for i in range(1, 51):
            img_path = os.path.join('static', f'{key}_{i}.jpg')
            if os.path.exists(img_path):
                os.remove(img_path)

        return key

    return ''
def get_attendance_data(className):
    # Connect to the Redis database
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    # Get the list from Redis
    list_key = 'tryAttendwithSub'  # Replace with your actual list key
    list_data = r.lrange(list_key, 0, -1)
    print(list_data)
    print(className)

    # Convert the byte strings to regular strings
    list_data = [item.decode('utf-8') for item in list_data]

    # Filter data for the latest seven days
    today = datetime.datetime.now().date()
    latest_seven_days = [today - datetime.timedelta(days=i) for i in range(7)]
    print(latest_seven_days)
    latest_seven_days_data = [
    item for item in list_data if len(item.split('@')) >= 4 and datetime.datetime.strptime(item.split('@')[-2], "%Y-%m-%d %H:%M:%S.%f").date() in latest_seven_days
    ]

    # Extract names from the filtered data and count their occurrences
    name_counts = Counter([item.split('@')[0] for item in latest_seven_days_data if item.split('@')[-1] == className])
    print(name_counts)

    # Create a dictionary with name as key and count as value
    result_dict = {name: count for name, count in name_counts.items()}
    print(result_dict)

    return result_dict


def generate_csv(data_dict):
    # Create a CSV file with the data
    csv_data = [['Name', 'Days Present']]
    for name, count in data_dict.items():
        csv_data.append([name, count])
    print(data_dict)
    # Generate the CSV file
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerows(csv_data)

    return csv_buffer.getvalue()

def update_field_name(old_field, new_field_name, r):
    # Specify the key
    key = 'academy:register'

    # Check if the old field exists in the hash
    if r.hexists(key, old_field.encode()):
        # Get the value of the old field
        value = r.hget(key, old_field.encode())

        # Split the field to extract the name and role parts
        name, role = old_field.split('@')

        # Combine the new field name with the role part
        new_field = f'{name}@{new_field_name}'

        # Delete the old field
        r.hdel(key, old_field.encode())

        # Set the value to the new field
        r.hset(key, new_field.encode(), value)

        return "Field name updated successfully."
    else:
        return "Old field does not exist."
    


unique_values2 = []

def process_image(image_path):
    frame = cv2.imread(image_path)
    try:
        pred_frame, names = face_rec.face_prediction(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)
        for name, role in names:
            if name and name != 'Unknown':
                print(name)
                print(unique_values2)
            if name == 'Unknown':
                continue
            value = name
            if not value:
                return

            # Generate the unique value with datetime
            unique_value = f"{value}@{role}@{datetime.datetime.now()}"
            # Extract the value without datetime for comparison
            extracted_value = value.split("@")[0]
            # Check if the extracted value is already present in the list
            if extracted_value not in [val.split("@")[0] for val in unique_values2]:
                unique_values2.append(unique_value)
            print(f"{unique_values2}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    ret, buffer = cv2.imencode('.jpg', pred_frame)
    frame = buffer.tobytes()
    print(unique_values2)
    
    # unique_values = []

    return frame, unique_values2

# Define the function to process frames and detect faces
def process_frames(frame, retrive_df, className):
    # Perform face recognition on the frame using the provided dataset
    pred_frame, names = face_rec.face_prediction(frame, retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)
    
    # Process the recognized faces
    for name, role in names:
        if name and name != 'Unknown':
            print(name)
            print(unique_values)

        value = name
        if not value:
            break

        # Generate the unique value with datetime and class name
        unique_value = f"{value}@{role}@{datetime.datetime.now()}"
        # Extract the value without datetime for comparison
        extracted_value = value.split("@")[0]
        
        # Check if the extracted value is already present in the list
        if extracted_value not in [val.split("@")[0] for val in unique_values]:
            unique_values.append(unique_value)
    
    # Return the processed data
    return unique_values
className=''

def generate_frames_for_register():
    cap = cv2.VideoCapture(1)  # 0 for default camera, 1 for external camera

    while True:
        ret, frame = cap.read()

        if not ret:
            break
        try:
            pred_frame, names = face_rec.face_prediction(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)
            # print(face_rec.face_prediction(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5))
            for name, role in names:
                if name and name !='Unknown':
                    print(name)
                    print(unique_values)
                    value = name
                    if not value:
                        break

                    # Generate the unique value with datetime
                    unique_value = f"{value}@{role}@{datetime.datetime.now()}"
                    # Extract the value without datetime for comparison
                    extracted_value = value.split("@")[0]
                    # Check if the extracted value is already present in the list
                    if extracted_value not in [val.split("@")[0] for val in unique_values]:
                        unique_values.append(unique_value)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            continue
        
        ret, buffer = cv2.imencode('.jpg', pred_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()