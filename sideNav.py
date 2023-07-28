import datetime
import io
from flask import Flask, render_template, request, redirect, session, url_for, Response, flash, jsonify
import cv2
import os
import numpy as np
from PIL import Image

import csv
import face_rec
import redis
from insightface.app import FaceAnalysis
import face_recognition
import faceRegistration as fr

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
app.secret_key = 'secret_key'

# Main crash page
@app.route('/')
def index():
    if 'username' in session:
        if session['username'] == 'admin':
            return redirect('/changeFields')
        elif session['username'] != '' and session['password'] == 'teacher':
            print(session['username'])
            return redirect(url_for("startClass"))
    return redirect(url_for('login'))

# List of all subjects taught by teacher
@app.route('/startClass')
def startClass():
    if "username" in session and session['password']=='teacher' and session['username']!='':
        r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
        face_rec.extract_data()
        fr.unique_values=[]
        # Retrieve field names and classes from the Redis database
        fields = r.hgetall('Teacher')
        fields = {key.decode(): value.decode() for key, value in fields.items()}
        return render_template('startAttendance.html', fields=fields)
    else:
        return redirect('url_for(login)')

# Login Page
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

# Backend attendance camera (move to last)
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

#backend register camera and form(move to last)
@app.route('/page2')
def page2():
    return render_template('faceregflask.html')

from faceRegistration import get_attendance_data, generate_csv, process_image

# Retrieve subject names and students present in each class
@app.route('/table')
def table():
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    fields = r.hgetall('Teacher')
    fields = {key.decode(): value.decode() for key, value in fields.items()}
    for field, class_names in fields.items():
        print(field)
    if session['username']=='admin':
        list_data = r.lrange('tryAttendwithSub', 0, -1)
        fields = fr.calculate_attendance(list_data)
        return render_template('adminTable.html', fields=fields)
    elif session['username']!='':
        return render_template('Tables.html', fields=fields)
    else:
        return redirect(url_for('login'))

# show table of present students
@app.route('/page3/<className>', methods=['GET', 'POST'])
def page3(className):
    result_dict = get_attendance_data(className)
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    list_data = r.lrange('tryAttendwithSub', 0, -1)
    print(f"result_dict={result_dict}")
    if request.method == 'POST':
        # Generate the CSV file
        csv_data = generate_csv(result_dict)
        # Prepare the response with the CSV file
        response = Response(csv_data, mimetype='text/csv')
        response.headers.set('Content-Disposition', 'attachment', filename='attendance.csv')
        return response
    return render_template('attendance.html', names=result_dict, className=className)

#log out form
@app.route('/logout')
def logout():
    # Clear the 'username' session variable
    session.pop('username', None)
    session['username'] = ''
    session['password'] = ''
    # Redirect the user to the login page
    return redirect(url_for('login'))

# admin panel - displays names of faces registered
@app.route('/changeFields', methods=['POST', 'GET'])
def changeField():
    # Connect to the Redis database
    r = redis.Redis(host='redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com', port=12084, password='HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd', db=0)
    if session['username'] != 'admin':
        return redirect(url_for('login'))
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
    fr.names=[]
    return render_template('index69.html', className=className)

# Route to receive video frames
# unique_values=[]
@app.route('/process_js_frames', methods=['POST','GET'])
def process_js_frames():
    # Get the video frame from the request
    frames = request.files['video_frame']

    image = Image.open(io.BytesIO(frames.read()))

    # Convert the Image object to a numpy array suitable for face recognition
    frame = np.array(image)

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
                fr.names.append(extracted_value)
    # Prepare the response
    response = {
        'report': fr.unique_values,
        'names': fr.names
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

@app.route('/frontRegister')
def frontRegister():
    file_names = os.listdir("static")
    for file_name in file_names:
            file_path = os.path.join('static', file_name)
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                os.remove(file_path)
                print(f"Deleted: {file_path}")
    return render_template('register.html')

count = 0  # Initialize the count variable

@app.route('/registerPeople', methods=['POST'])
def register_people():
    # Access the global count variable
    global count

    frames = request.files.getlist('video_frame')
    save_directory = f'static'

    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    print(count)

    for frame in frames:
        # if count >= 100:
        #     return redirect(url_for('frontAttend'))  # Redirect to "frontAttend" when 100 frames are saved
        
        # Generate a unique file name using timestamp and count
        # timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        timestamp = datetime.datetime.now()
        save_path = os.path.join(save_directory, f'frame_{timestamp}_{count}.jpg')
        count+=1

        # Save the frame to the static folder
        frame.save(save_path)
    return "pic capturing"

capture_count=0
face_embeddings=[]
@app.route('/submitRegister', methods=['POST', 'GET'])
def submitRegister():
    global capture_count, face_embeddings
    # print("hello world")
    if request.method == 'POST':
        # Process login form data here
        name = request.form['name']
        print(name)
    fr.registerPerson(name)
    key = name + '@' + "student"



    return render_template("registerSuccessful.html")



#Backend Video feed 
@app.route('/video_feed')
def video_feed():
    return Response(fr.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#Download CSV file
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

@app.route('/spoofFrontAttend/<className>')
def spoofFrontAttend(className):
    print("classname=%s"%className)
    fr.unique_values = []
    fr.names=[]
    return render_template('spoofAttend.html', className=className)

@app.route('/process_js_frames_spoof', methods=['POST','GET'])
def process_js_frames_spoof():
    # Get the video frame from the request
    frames = request.files['video_frame']
    
    image = Image.open(io.BytesIO(frames.read()))

    # Convert the Image object to a numpy array suitable for face recognition
    frame = np.array(image)

    pred_frame, names, tcount= face_rec.face_predictionss(frame, face_rec.retrive_df, 'facial_features', ['Name', 'Role'], thresh=0.5)

    for name, role in names:
        if name and name !='Unknown':
        #     if total_counts[name]["Real"]+total_counts[name]["Fake"]>=10:
        #         if total_counts[name]["Real"]>total_counts[name]["Fake"]:

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
                        fr.names.append(extracted_value)
    # Prepare the response
    response = {
        'report': fr.unique_values,
        'names': fr.names,
        't_count': tcount
        # Add any other relevant data or results here
    }

    return jsonify(response)

@app.route('/inn')
def insect():
	return render_template('sideNavNew.html')

if __name__ == "__main__":
    # Generate self-signed SSL certificate
    import ssl
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="/Users/shashankpandey/Downloads/cameraTry/cert.pem", keyfile="/Users/shashankpandey/Downloads/cameraTry/key.pem")
    
    # Run Flask app with HTTPS enabled
    app.run(ssl_context=ssl_context, host="0.0.0.0", port=6009, debug=True)
    # app.run( host="0.0.0.0", port=6009, debug=True)