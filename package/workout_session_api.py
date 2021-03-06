from package import app
from flask import request, Response
import mariadb
import dbcreds
import json
import datetime

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

def get_session():
    params_id = request.args.get("userId")
    if (params_id is None):
        return Response("'GET' Api requires parameters",
                                    mimetype="text/plain",
                                    status=400)

    elif (params_id is not None):
        try:
            cnnct_to_db = MariaDbConnection()
            cnnct_to_db.connect()
        except ConnectionError:
            cnnct_to_db.endConn()
            return Response("Error while attempting to connect to the database",
                                        mimetype="text/plain",
                                        status=400)
        try:
            params_id = int(request.args.get("userId"))
        except ValueError:
            cnnct_to_db.endConn()
            return Response("Incorrect datatype received",
                                        mimetype="text/plain",
                                        status=400)
    
        if ((0< params_id<99999999)):
            cnnct_to_db.cursor.execute("SELECT * FROM workout_session WHERE user_id =?", [params_id])
            session_match = cnnct_to_db.cursor.fetchone()

            if (session_match is not None):
                content = {
                        'id': session_match[0],
                        'session_token': session_match[1],
                        'startedAt': session_match[2],
                        'workoutId': session_match[3],
                        'userId' : session_match[4],
                        }
                cnnct_to_db.endConn()
                return Response(json.dumps(content, default=str),
                                    mimetype="application/json",
                                    status=200)
            else:
                cnnct_to_db.endConn()
                return Response(
                                mimetype="text/plain",
                                status=204)
            
        else:
            cnnct_to_db.endConn()
            return Response("Invalid parameters. ID Must be an integer",
                                    mimetype="text/plain",
                                    status=400)

def post_session():
    data = request.json
    #Create a session token
    #Create Start Time
    client_loginToken = data.get('loginToken')
    client_workoutId = data.get('workoutId')
    client_userId = data.get('userId')
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        #Check loginToken
        cnnct_to_db.cursor.execute("SELECT loginToken FROM user_session WHERE loginToken=?",[client_loginToken])
        match = cnnct_to_db.cursor.fetchone()
        #Only returns one row, so only one combination is valid
        if match == None:
            return Response("User login invalid",
                            mimetype="plain/text",
                            status=400)

    except ConnectionError:
        cnnct_to_db.endConn()
        return Response("Error while attempting to connect to the database",
                        mimetype="text/plain",
                        status=444)  
    except mariadb.DataError:
        cnnct_to_db.endConn()
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
    except mariadb.IntegrityError:
        cnnct_to_db.endConn()
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)

    #create unique login token
    import uuid
    generateUuid = uuid.uuid4().hex
    str(generateUuid)

    try:
        #get current date and time
        started_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cnnct_to_db.cursor.execute("INSERT INTO workout_session(started_at,session_token,workout_id,user_id) VALUES(?,?,?,?)",[started_at,generateUuid,client_workoutId,client_userId])
        cnnct_to_db.conn.commit()

        cnnct_to_db.cursor.execute("SELECT * FROM workout_session WHERE user_id=? ORDER BY id DESC LIMIT 1",[client_userId])
        result = cnnct_to_db.cursor.fetchone()

        resp = {
            "sessionId": result[0],
            "sessionToken": result[1],
            "startedAt": result[2],
            "workoutId": result[3],
            "userId": result[4]
        }

        return Response(json.dumps(resp, default=str),
                                    mimetype="application/json",
                                    status=201)
    except mariadb.DataError:
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
    except mariadb.IntegrityError:
            print("Something wrong with your data")
            return Response("Something wrong with your data",
                            mimetype="text/plain",
                            status=400)
    finally:
        cnnct_to_db.endConn()

def remove_session():
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
        {   'name': 'userId',
            'datatype': int,
            'maxLength': 10,
            'required': True
        },
        
    ]
    validate_data(requirements,data)
    check_data_required(requirements,data)

    client_loginToken = data.get('loginToken')
    client_userId = data.get('userId')
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()

        cnnct_to_db.cursor.execute("SELECT loginToken FROM user_session WHERE loginToken=?",[client_loginToken])
        match = cnnct_to_db.cursor.fetchone()
        #Only returns one row, so only one combination is valid
        if match == None:
            return Response("User login invalid",
                            mimetype="plain/text",
                            status=400)

        cnnct_to_db.cursor.execute("DELETE FROM workout_session WHERE user_id=? ",[client_userId])
        cnnct_to_db.conn.commit()
        cnnct_to_db.endConn()
        
        return Response("Session Deleted",
                        mimetype="text/plain",
                        status=204)
    except ConnectionError:
        print("Error while attempting to connect to the database")
        return Response("Error while attempting to connect to the database",
                        mimetype="text/plain",
                        status=444)  
    except mariadb.DataError:
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)

@app.route('/api/workout-session', methods=['GET', 'POST', 'DELETE'])
def workout_session_api():
    if (request.method == 'GET'):
        return get_session()
    elif (request.method == 'POST'):
        return post_session()
    elif (request.method == 'DELETE'):
        return remove_session()
    else:
        print("Something went wrong with the login API.")
