import time
import numpy as np
import pandas as pd
import cv2
import datetime
import redis
import insightface
from spoofDetect.test import test

# insight face
from insightface.app import FaceAnalysis
from sklearn.metrics import pairwise

# Connect to Redis Client
hostname = 'redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com'
portnumber = 12084
password = 'HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd'

r = redis.StrictRedis(host=hostname, port=portnumber, password=password)


# configure face analysis
faceapp = FaceAnalysis(name='buffalo_sc',root='/Users/shashankpandey/Downloads/Notes/2_Fast_Face_Recognition_System/insightface_model', providers = ['CPUExecutionProvider'])
faceapp.prepare(ctx_id = 0, det_size=(640,640), det_thresh = 0.5)

# ML Search Algorithm
def ml_search_algorithm(dataframe,feature_column,test_vector,
                        name_role=['Name','Role'],thresh=0.5):
    """
    cosine similarity base search algorithm
    """
    # step-1: take the dataframe (collection of data)
    dataframe = dataframe.copy()
    # step-2: Index face embeding from the dataframe and convert into array
    X_list = dataframe[feature_column].tolist()
    x = np.asarray(X_list)
    
    # step-3: Cal. cosine similarity
    similar = pairwise.cosine_similarity(x,test_vector.reshape(1,-1))
    similar_arr = np.array(similar).flatten()
    dataframe['cosine'] = similar_arr

    # step-4: filter the data
    data_filter = dataframe.query(f'cosine >= {thresh}')
    if len(data_filter) > 0:
        # step-5: get the person name
        data_filter.reset_index(drop=True,inplace=True)
        argmax = data_filter['cosine'].argmax()
        person_name, person_role = data_filter.loc[argmax][name_role]
        
    else:
        person_name = 'Unknown'
        person_role = 'Unknown'
        
    return person_name, person_role


def face_prediction(test_image, dataframe,feature_column,
                        name_role=['Name','Role'],thresh=0.5):
    names=roles=[]
    # step-1: take the test image and apply to insight face
    results = faceapp.get(test_image)
    print(results)
    test_copy = test_image.copy()
    # step-2: use for loop and extract each embedding and pass to ml_search_algorithm

    for res in results:
        x1, y1, x2, y2 = res['bbox'].astype(int)
        embeddings = res['embedding']
        person_name, person_role = ml_search_algorithm(dataframe, feature_column, test_vector=embeddings, name_role=name_role,
                                                       thresh=thresh)
        if person_name == 'Unknown':
            color =(0,0,255) # bgr
        else:
            color = (0,255,0)

        cv2.rectangle(test_copy,(x1,y1),(x2,y2),color)

        text_gen = person_name
        current_datetime = datetime.datetime.now()
        date = str(current_datetime.date())+str(current_datetime.time())
        # date = str(date)
        pname=person_name
        role = person_role
        person_name = person_name + date
        roles=[pname, role]
        names.append(roles)

        cv2.putText(test_copy,text_gen,(x1,y1),cv2.FONT_HERSHEY_DUPLEX,0.7,color,2)
        cv2.putText(test_copy,date,(x2,y2),cv2.FONT_HERSHEY_DUPLEX,0.7,color,2)
        # print(date)
        # print(person_name)


    return test_copy, names

# import datetime

# # Create a datetime object

# # Get the date from the datetime object
# date = current_datetime.date()

# # Print the date
# print(date)
# %%
import face_rec

# %%
import redis


# %%
import pandas as pd
import numpy as np
import cv2

# %%
hostname = 'redis-12084.c301.ap-south-1-1.ec2.cloud.redislabs.com'
portnumber = 12084
password = 'HnYyQx7B7hqPWS0OvE45nVAMm48xzkRd'

r = redis.StrictRedis(host=hostname,
                      port=portnumber,
                      password=password)
r.ping()

# #### Step-1: Extract Data from database
def extract_data():
    global retrive_df
    name = 'academy:register'
    retrive_dict= r.hgetall(name)
    retrive_series = pd.Series(retrive_dict)
    retrive_series = retrive_series.apply(lambda x: np.frombuffer(x,dtype=np.float32))
    index = retrive_series.index
    index = list(map(lambda x: x.decode(), index))
    retrive_series.index = index
    retrive_df =  retrive_series.to_frame().reset_index()
    retrive_df.columns = ['name_role','facial_features']
    retrive_df[['Name','Role']] = retrive_df['name_role'].apply(lambda x: x.split('@')).apply(pd.Series)
    retrive_df
extract_data()
print(retrive_df)


def face_predictions(test_image, dataframe, feature_column, name_role=['Name', 'Role'], thresh=0.5):
    names = []
    roles = []
    total_story=[]
    # step-1: take the test image and apply to insight face
    results = faceapp.get(test_image)
    print(results)
    test_copy = test_image.copy()
    # step-2: use for loop and extract each embedding and pass to ml_search_algorithm

    for res in results:
        x1, y1, x2, y2 = res['bbox'].astype(int)
        a=y1-80
        b=y2-80
        # face_image = test_image[y1:int(4*y1/3), x1:int(4*x1/3)]  # Crop the face region
        # y4 = min(y1 + int((4 / 3) * (x2 - x1)), test_image.shape[0])
        # x4 = min(x1 + int((3 / 4) * (y2 - y1)), test_image.shape[1])
        y3=int(y2*1.4)
        x3=int(x2*1.4)
        face_image = test_image[int(y1/2):y3, int(x1/2):x3]


        # Perform the spoof detection on the cropped face
        label = test(image=face_image,
                     model_dir='/Users/shashankpandey/Downloads/spoofsss/spoofDetect/resources/anti_spoof_models',
                     device_id=0)

        if label == 1:
            # Face is real
            color = (0, 255, 0)
            text_gen = 'Real'
        else:
            # Face is a spoof
            color = (0, 0, 255)
            text_gen = 'Fake'

        cv2.rectangle(test_copy, (x1, y1), (x2, y2), color)
        cv2.rectangle(test_copy, (int(x1/2), int(y1/2)), (x3,y3), (0,0,0))
        cv2.putText(test_copy, text_gen, (x1+40, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        # Get the person name and role using ml_search_algorithm
        embeddings = res['embedding']
        person_name, person_role = ml_search_algorithm(dataframe, feature_column, test_vector=embeddings,
                                                       name_role=name_role, thresh=thresh)

        if person_name == 'Unknown':
            color = (0, 0, 255)  # bgr
        else:
            color = (0, 255, 0)

        # cv2.putText(test_copy, person_name, (x1, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
        # cv2.putText(test_copy, person_role, (x2, y2), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        current_datetime = datetime.datetime.now()
        date = str(current_datetime.date()) + str(current_datetime.time())
        pname = person_name
        role = person_role
        person_name = person_name + date
        roles = [pname, role]

        names.append(roles)

    return test_copy, names

names = []
total_counts = {}
t_counts={}
def face_predictionss(test_image, dataframe, feature_column, name_role=['Name', 'Role'], thresh=0.5):
    # names = []
    # total_counts = {}
    global names, total_counts, t_counts
    # step-1: take the test image and apply to insight face
    results = faceapp.get(test_image)
    print(results)
    test_copy = test_image.copy()
    
    # step-2: use for loop and extract each embedding and pass to ml_search_algorithm
    for res in results:
        x1, y1, x2, y2 = res['bbox'].astype(int)
        a = y1 - 80
        b = y2 - 80
        
        y3 = int(y2 * 1.4)
        x3 = int(x2 * 1.4)
        face_image = test_image[int(y1 / 2):y3, int(x1 / 2):x3]

        # Perform the spoof detection on the cropped face
        label = test(image=face_image,
                     model_dir='/Users/shashankpandey/Downloads/spoofsss/spoofDetect/resources/anti_spoof_models',
                     device_id=0)

        if label == 1:
            # Face is real
            color = (0, 255, 0)
            text_gen = 'Real'
        else:
            # Face is a spoof
            color = (0, 0, 255)
            text_gen = 'Fake'

        cv2.rectangle(test_copy, (x1, y1), (x2, y2), color)
        cv2.rectangle(test_copy, (int(x1 / 2), int(y1 / 2)), (x3, y3), (0, 0, 0))
        cv2.putText(test_copy, text_gen, (x2, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        # Get the person name and role using ml_search_algorithm
        embeddings = res['embedding']
        person_name, person_role = ml_search_algorithm(dataframe, feature_column, test_vector=embeddings,
                                                       name_role=name_role, thresh=thresh)

        if person_name == 'Unknown':
            color = (0, 0, 255)  # bgr
        else:
            color = (0, 255, 0)

        cv2.putText(test_copy, person_name, (x1, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
        cv2.putText(test_copy, person_role, (x2, y2), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)


        current_datetime = datetime.datetime.now()
        date = str(current_datetime.date()) + str(current_datetime.time())
        pname = person_name
        role = person_role
        person_name = person_name + date
        roles = [pname, role]
        names.append(roles)

        if pname not in total_counts:
            total_counts[pname] = {'Real': 0, 'Fake': 0}

        total_counts[pname][text_gen] += 1
        if total_counts[pname]['Real']+ total_counts[pname]['Fake']>=10:
            t_counts=total_counts

    for name, counts in t_counts.items():
        print(f"{name}: {counts}")
        print(total_counts)

    return test_copy, names, t_counts
