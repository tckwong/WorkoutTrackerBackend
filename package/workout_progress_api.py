from package import app
from flask import request, Response
import mariadb
import dbcreds
import json

class MariaDbConnection:    
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = mariadb.connect(
        user=dbcreds.user, 
        password=dbcreds.password, 
        host=dbcreds.host,
        port=dbcreds.port, 
        database=dbcreds.database)
        self.cursor = self.conn.cursor()

    def endConn(self):
        #Check if cursor opened and close all connections
        if (self.cursor != None):
            self.cursor.close()
        if (self.conn != None):
            self.conn.close()

class RequiredDataNull(Exception):
    def __init__(self):
        super().__init__("Missing required data")

class DataOutofBounds(Exception):
    def __init__(self):
        super().__init__("Please check your inputs. Data is out of bounds")

def check_data_required(requiredSet, data):
    #Check if required
    checklist=[]
    for item in requiredSet:
        if(item.get('required') == True):
            checklist.append(item.get('name'))
    
    # Checks data received are in checklist
    if not (data.keys() <= set(checklist)):
        raise RequiredDataNull()

def validate_data(mydict, data):
    for item in data.keys():
        newlst = []
        for obj in mydict:
            x = obj.get('name')
            newlst.append(x)
            
        found_index = newlst.index(item)
        
        if item in mydict[found_index]['name']:
            #Check for correct datatype
            data_value = data.get(item)
            chk = isinstance(data_value, mydict[found_index]["datatype"])
            if not chk:
                raise TypeError()

            #Check for max char length
            maxLen = mydict[found_index]['maxLength']
            if(type(data.get(item)) == str and maxLen != None):
                if(len(data.get(item)) > maxLen):
                    raise DataOutofBounds
        else:
            raise ValueError

def get_workout_progress():
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
    except ConnectionError:
        cnnct_to_db.endConn()
        return Response("Error while attempting to connect to the database",
                                    mimetype="text/plain",
                                    status=400)
    params_id = request.args

    if (params_id is None):
        cnnct_to_db.endConn()
        return Response("Please provide a userId",
                                mimetype="text/plain",
                                status=400)

    elif (params_id is not None):
        cnnct_to_db.cursor.execute("SELECT exercise_name,weight,completed_at FROM completed_exercises INNER JOIN completed_workouts ON completed_exercises.completed_workout_id=completed_workouts.id WHERE completed_exercises.user_id =? AND exercise_name=?", [params_id.get('userId'),params_id.get('exerciseName')])
        exerciseList = cnnct_to_db.cursor.fetchall()
        list = []
        content = {}
        for result in exerciseList:
            content = { 'exerciseName': result[0],
                        'weight': result[1],
                        'completedAt' : result[2]
                    }
            list.append(content)

        cnnct_to_db.endConn()
        return Response(json.dumps(list, default=str),
                                    mimetype="application/json",
                                    status=200)

@app.route('/api/workout-progress', methods=['GET','DELETE'])
def workout_progress_api():
    if (request.method == 'GET'):
        return get_workout_progress()
    else:
        print("Something went wrong with the login API.")