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

def get_workout_history():
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
    except ConnectionError:
        cnnct_to_db.endConn()
        return Response("Error while attempting to connect to the database",
                                    mimetype="text/plain",
                                    status=400)
    params_id = request.args.get("userId")

    if (params_id is None):
        cnnct_to_db.endConn()
        return Response("Please provide a userId",
                                mimetype="text/plain",
                                status=400)

    elif (params_id is not None):
        try:
            params_id = int(request.args.get("userId"))
        except ValueError:
            cnnct_to_db.endConn()
            return Response("Incorrect datatype received",
                                        mimetype="text/plain",
                                        status=400)
    
        if ((0< params_id<9999999)):
            cnnct_to_db.cursor.execute("SELECT * FROM completed_workouts INNER JOIN completed_exercises ON completed_exercises.completed_workout_id = completed_workouts.id WHERE completed_workouts.user_id =?", [params_id])
            workoutList = cnnct_to_db.cursor.fetchall()
            # First I made a list of tuples with 
            newList = []
            for count, value in enumerate(workoutList):
                # Tuple of completed_workout_ids - the unique identifier in the data
                newTuple = (workoutList[count][9],)
                newList += newTuple
            # Creating my dictionary that stores the count of each number of rows pertaining to each completed workoutId
            dict_of_counts = {item:newList.count(item) for item in newList}

            # converting the tuples into a plain list
            listofCounts = dict_of_counts.values()
            final_list = list(listofCounts)
    
            i = 0
            appendedList = []
            # Value is the number of exercises per workout
            for count, value in enumerate(final_list):
                resultDict = {
                "workoutTitle" : [],
                "completedAt" : [],
                "exerciseName" : [],
                "reps":[],
                "sets":[],
                "weight":[],
            }   
                # Inner loop loops through the length of value being the number of exercises
                for reps1 in range(value):
                    resultDict["workoutTitle"].append(workoutList[i][1])
                    resultDict["completedAt"].append(workoutList[i][2])
                    resultDict["exerciseName"].append(workoutList[i][5])
                    resultDict["reps"].append(workoutList[i][6])
                    resultDict["sets"].append(workoutList[i][7])
                    resultDict["weight"].append(workoutList[i][8])
                    i+=1
                appendedList.append(resultDict)
                
            cnnct_to_db.endConn()
        else:
            cnnct_to_db.endConn()
            return Response("Invalid parameters. ID Must be an integer",
                                    mimetype="text/plain",
                                    status=400)

        return Response(json.dumps(appendedList, default=str),
                                    mimetype="application/json",
                                    status=200)

@app.route('/api/workout-history', methods=['GET'])
def workout_history_api():
    if (request.method == 'GET'):
        return get_workout_history()
    else:
        print("Something went wrong with the login API.")