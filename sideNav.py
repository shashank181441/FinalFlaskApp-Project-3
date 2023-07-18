import datetime
import io
from flask import Flask, render_template, request, redirect, session, url_for, Response, flash, jsonify
import cv2
import os
import numpy as np
from PIL import Image

import face_rec
import redis
from insightface.app import FaceAnalysis
import face_recognition
import faceRegistration as fr

app = Flask(__name__)

r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
app.secret_key = 'secret_key'

@app.route('/')
def index():
    if 'username' in session:
        if session['username'] == 'admin':
            return redirect('/changeFields')
        elif session['username'] != '':
            return redirect(url_for("startClass"))
    return redirect(url_for('login'))

@app.route('/startClass')
def startClass():
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    face_rec.extract_data()
    fr.unique_values=[]
    # Retrieve field names and classes from the Redis database
    fields = r.hgetall('Teacher')
    fields = {key.decode(): value.decode() for key, value in fields.items()}
    return render_template('startAttendance.html', fields=fields)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Process login form data here
        username = request.form['username']
        password = request.form['password']
        users = []
        r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

        fields = r.hgetall('Teacher')
        fields = {key.decode(): value.decode() for key, value in fields.items()}

        for field, class_names in fields.items():
            users.append(field)

        # Check if the username and password are valid (example logic)
        if username == 'admin' and password == 'admin':
            # Set the user in the session
            session['username'] = username
            return redirect('/')  # Redirect to the dashboard page
        elif username in users and password == 'teacher':
            session['username'] = username
            session['password'] = password
            return redirect('/')
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/video_feed')
def video_feed():
    return Response(fr.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed_for_register')
def video_feed_for_register():
    return Response(fr.generate_frames_for_register(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture', methods=['POST'])
def capture():
    person_name = request.form['name']
    role = request.form['role']

    key = fr.capture_photos(person_name, role)

    if key:
        return redirect(url_for('success', key=key))
    else:
        return 'No facial embeddings captured.'

@app.route('/success/<key>')
def success(key):
    img_files = [f'{key}_{i}.jpg' for i in range(1, 51)]
    return render_template('success.html', key=key, img_files=img_files)

@app.route('/page1/<className>')
def page1(className):
    fr.unique_values=[]
    return render_template('page1.html', className=className)

@app.route('/attend', methods=['POST'])
def handle_attend_form():
    className = request.form['className']
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    list_key = 'tryAttendwithSub'  # Replace with your actual list key

    updated_values = []
    print(f"unique values: {fr.unique_values}" )
    for value in fr.unique_values:
        updated_value = f"{value}@{className}"
        updated_values.append(updated_value)

    # r.lpush(list_key, *updated_values)
    for uvalue in updated_values:
        r.lpush(list_key, uvalue)
        print(f"Updated Value:{uvalue}")
    fr.unique_values = []
    return render_template('todayAttendance.html', unique_values=updated_values)

@app.route('/page2')
def page2():
    return render_template('faceregflask.html')

from faceRegistration import get_attendance_data, generate_csv, process_image

@app.route('/page3/<className>', methods=['GET', 'POST'])
def page3(className):
    result_dict = get_attendance_data(className)
    
    if request.method == 'POST':
        # Generate the CSV file
        csv_data = generate_csv(result_dict)
        # Prepare the response with the CSV file
        response = Response(csv_data, mimetype='text/csv')
        response.headers.set('Content-Disposition', 'attachment', filename='attendance.csv')
        return response
    return render_template('attendance.html', names=result_dict, className=className)

import csv

@app.route('/download_csv')
def download_csv():
    # Create a CSV file with the data
    csv_data = [['Name', 'Days Present']]
    for name, count in names.items():
        csv_data.append([name, count])

    # Generate the CSV file and send it as a response
    response = Response(content_type='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='attendance.csv')

    writer = csv.writer(response)
    writer.writerows(csv_data)

    return response

@app.route('/logout')
def logout():
    # Clear the 'username' session variable
    session.pop('username', None)
    # Redirect the user to the login page
    return redirect(url_for('login'))


@app.route('/changeFields', methods=['POST', 'GET'])
def changeField():
    # Connect to the Redis database
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    # Handle form submission
    if request.method == 'POST':
        # Get the form data
        old_field = request.form['old_field']
        new_field_name = request.form['new_field']
        # Call the update_field_name function
        result = fr.update_field_name(old_field, new_field_name, r)
        return result

    # Retrieve field names for displaying in the HTML template
    fields = r.hkeys('academy:register')
    fields = [field.decode() for field in fields]
    teachers=r.hkeys('Teacher')
    teachers = [teacher.decode() for teacher in teachers]
    for teacher in teachers:
        teacher += "@Teacher"
        fields.append(teacher)
    print(teachers, fields)
    return render_template('changeFields.html', fields=fields)

@app.route('/table')
def table():
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    fields = r.hgetall('Teacher')
    fields = {key.decode(): value.decode() for key, value in fields.items()}
    for field, class_names in fields.items():
        print(field)
    return render_template('Tables.html', fields=fields)

@app.route('/summary', methods=['POST', 'GET'])
def summary():
    # Connect to the Redis database
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    # Retrieve field names for displaying in the HTML template
    fields = r.hkeys('academy:register')
    fields = [field.decode() for field in fields]
    return render_template('summary.html', fields=fields)

@app.route('/subjects', methods=['POST', 'GET'])
def subjects():
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    # Retrieve field names and classes from the Redis database
    fields = r.hgetall('Teacher')
    fields = {key.decode(): value.decode() for key, value in fields.items()}
    return render_template('subjects.html', fields=fields)

@app.route('/subjectEdit', methods=['POST', 'GET'])
def subjectEdit():
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)

    # Handle form submission
    if request.method == 'POST':
        # Extract the submitted form data
        fields = request.form.getlist('field')
        classes = request.form.getlist('class')

        # Update the Redis database
        for field, class_name in zip(fields, classes):
            if field.strip() and class_name.strip():
                r.hset('Teacher', field, class_name)

        # Redirect back to the admin panel page
        return redirect('/subjects')

    # Retrieve field names and classes from the Redis database
    fields = r.hgetall('Teacher')
    fields = {key.decode(): value.decode() for key, value in fields.items()}

    return render_template('subjectEdit.html', fields=fields)

@app.route('/jjj/<className>')
def indexj(className):
    return render_template('index.html', className=className)

@app.route('/process/', methods=['GET','POST'])
def image_processing():
    # Check if an image file was uploaded

    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    list_key = 'tryAttendwithSub'  # Replace with your actual list key
    if request.method == 'POST':
        className = request.form['className']
    print(className)
    if 'image' not in request.files:
        return render_template('index.html', error='No image file uploaded')
    image = request.files['image']
    # print(request.files)
    print(image)
    images=request.files.getlist('image')
    print(images)
    
    # Check if the file is an image
    count=0
    for img in images:

        updated_values=[]
        if img.filename == '':
            return render_template('index.html', error='No image file selected')

        count+=1
    # Save the uploaded image
        image_path = f'processed_images/uploaded_image{count}.jpg'
        img.save(image_path)

    # Call the process_image function from image_processing.py
        processed_frame, unique_values2 = process_image(image_path)

        for value in unique_values2:
            updated_value = f"{value}@{className}"
            updated_values.append(updated_value)
    print (updated_values)
    fr.unique_values2=[]
    # r.lpush(list_key, *updated_values)
    for uvalue in updated_values:
        r.lpush(list_key, uvalue)
        print(f"Updated Value:{uvalue}")
    def generate():
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + processed_frame + b'\r\n')

    # Return the processed frame as a response
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/deleteTeacher/<name>')
def deleteTeacher(name):
    import redis

    # Connect to Redis Client
    hostname = 'redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com'
    portnumber = 12084
    password = 'HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd'

    r = redis.Redis(host=hostname, port=portnumber, password=password, db=0)

    # Name of the hash and field to delete
    hash_name = 'Teacher'
    field_to_delete = name
    realName = field_to_delete.replace('%20'," ")

    # Delete the field from the hash
    r.hdel(hash_name, realName)
    return redirect('/subjects')


@app.route('/frontAttend/<className>')
def frontAttend(className):
    print("classname=%s"%className)
    fr.unique_values = []
    return render_template('takeAttendance.html', className=className)

# Route to receive video frames
# unique_values=[]
@app.route('/process_js_frames', methods=['POST','GET'])
def process_js_frames():
    
    # Get the video frame from the request
    frames = request.files['video_frame']
    # Convert the video frame to a format suitable for face_recognition
    frame = face_recognition.load_image_file(frames)

    pred_frame, names= face_rec.face_prediction(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)
    print(names)
    for name, role in names:
        if name and name !='Unknown':
            print(name)
            print(fr.unique_values)

        # value = input("Enter a value (or press Enter to finish): ")
            value = name
            if not value:
                break

            # Generate the unique value with datetime
            unique_value = f"{value}@{role}@{datetime.datetime.now()}"
            # Extract the value without datetime for comparison
            extracted_value = value.split("@")[0]
            # Check if the extracted value is already present in the list
            if extracted_value not in [val.split("@")[0] for val in fr.unique_values]:
                fr.unique_values.append(unique_value)
    # Prepare the response
    response = {
        'report': fr.unique_values,
        # Add any other relevant data or results here
    }
    print(response)
    return jsonify(response)

@app.route('/submitFront', methods=['POST','GET'])
def submitFront():

    if request.method == 'POST':
        # Process login form data here
        className = request.form['className']
    hostname = 'redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com'
    portnumber = 12084
    password = 'HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd'

    r = redis.StrictRedis(host=hostname, port=portnumber, password=password)
    list_key = 'tryAttendwithSub' 

    print("unique values:")
    print(fr.unique_values)
    for uk in fr.unique_values:
        uk = f"{uk}@{className}"
        print(f"unique value: {uk}")
        r.lpush(list_key,uk)
    uks = fr.unique_values
    fr.unique_values=[]
    face_rec.total_counts= face_rec.t_counts= []
    return render_template('todayAttendance.html', unique_values=uks)

@app.route('/rough')
def rough():
    return render_template('rough.html')

if __name__ == "__main__":
    # Generate self-signed SSL certificate
    import ssl
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="/Users/shashankpandey/Downloads/cameraTry/cert.pem", keyfile="/Users/shashankpandey/Downloads/cameraTry/key.pem")
    
    # Run Flask app with HTTPS enabled
    app.run(ssl_context=ssl_context, host="0.0.0.0", port=6009, debug=True)
    # app.run( host="0.0.0.0", port=6009, debug=True)