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

def get_workouts():
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
        cnnct_to_db.cursor.execute("SELECT * FROM workout")
        workout_list = cnnct_to_db.cursor.fetchall()
        list = []
        content = {}
        for result in workout_list:
            content = { 
                        'workoutId': result[0],
                        'title': result[1],
                        'created_on' : result[2],
                        'completed' : result[3],
                        'completed_on' : result[4],
                        'userId' : result[5],
                        }
            list.append(content)

        cnnct_to_db.endConn()
        return Response(json.dumps(list, default=str),
                        mimetype="application/json",
                        status=200)
    elif (params_id is not None):
        try:
            params_id = int(request.args.get("userId"))
        except ValueError:
            cnnct_to_db.endConn()
            return Response("Incorrect datatype received",
                                        mimetype="text/plain",
                                        status=400)
    
        if ((0< params_id<9999999)):
            cnnct_to_db.cursor.execute("SELECT * FROM workout INNER JOIN user ON workout.user_id = user.id WHERE user.id =?", [params_id])
            workoutIdMatch = cnnct_to_db.cursor.fetchall()
            list = []
            content = {}
            for result in workoutIdMatch:
                content = { 
                        'workoutId': result[0],
                        'title': result[1],
                        'created_on' : result[2],
                        'completed' : result[3],
                        'completed_on' : result[4],
                        'userId' : result[5],
                        }
                list.append(content)
            cnnct_to_db.endConn()
        else:
            cnnct_to_db.endConn()
            return Response("Invalid parameters. ID Must be an integer",
                                    mimetype="text/plain",
                                    status=400)

        return Response(json.dumps(list, default=str),
                                    mimetype="application/json",
                                    status=200)

def post_workout():
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
        {   
            'name': 'title',
            'datatype': str,
            'maxLength': 40,
            'required': True
        },
    ]

    validate_data(requirements,data)
    check_data_required(requirements,data)
        

    client_loginToken = data.get('loginToken')
    client_title = data.get('title')

    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()

        #checkloginToken and get user Id
        cnnct_to_db.cursor.execute("SELECT user.id,title,created_on,completed,completed_on from user_session INNER JOIN user ON user_session.user_id = user.id INNER JOIN workout ON workout.user_id = user.id WHERE user_session.loginToken =?", [client_loginToken])
        session_match = cnnct_to_db.cursor.fetchone()
        #check for a row match check if user is loggeds in
        if session_match == None:
            return Response("No matching results were found",
                                mimetype="text/plain",
                                status=400)
        
        db_userId = session_match[0]
        # db_title = session_match[1]
        # db_created_on = session_match[2]
        # db_completed = session_match[3]
        # db_completed_on = session_match[4]

        #get current date
        cur_date = datetime.datetime.now().strftime('%Y-%m-%d')

        cnnct_to_db.cursor.execute("INSERT INTO workout(title,created_on,completed,user_id) VALUES(?,?,?,?)",[client_title,cur_date,0,db_userId])
        if(cnnct_to_db.cursor.rowcount == 1):
            cnnct_to_db.conn.commit()
        else:
            return Response("Failed to add workout",
                                mimetype="text/plain",
                                status=400)
        cnnct_to_db.cursor.execute("SELECT * from workout WHERE user_id=? ORDER BY id DESC LIMIT 1",[db_userId])
        inserted_data = cnnct_to_db.cursor.fetchone()
        resp = {
                "workoutId" : inserted_data[0],
                "title" : inserted_data[1],
                "created_on" : inserted_data[2],
                "completed" : inserted_data[3],
                "completed_on" : inserted_data[4],
                "userId" : inserted_data[5],
        }
        return Response(json.dumps(resp, default=str),
                                mimetype="application/json",
                                status=201)
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
    except mariadb.IntegrityError:
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
    finally:
        cnnct_to_db.endConn()

def patch_workout():
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
        {   
            'name': 'workoutId',
            'datatype': int,
            'maxLength': 2,
            'required': True
        },
        {   
            'name': 'title',
            'datatype': str,
            'maxLength': 40,
            'required': False
        },
        {
            'name': 'completed',
            'datatype': int,
            'maxLength': 1,
            'required': False
        }
    ]
    # "validate_data(requirements,data)
    # check_data_required(requirements,data)"

    client_loginToken = data.get('loginToken')
    client_workoutId = data.get('workoutId')
    client_title = data.get('title')
    client_completed = data.get('completed')
    
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        #Check for workout ownership
        cnnct_to_db.cursor.execute("SELECT user.id,title,created_on,completed,completed_on from user_session INNER JOIN user ON user_session.user_id = user.id INNER JOIN workout ON workout.user_id = user.id WHERE user_session.loginToken =? AND workout.id=?", [client_loginToken,client_workoutId])
        info_match = cnnct_to_db.cursor.fetchone()
        if not info_match:
            cnnct_to_db.endConn()
            return Response("No matching results were found",
                                mimetype="text/plain",
                                status=400)

        for key in data:
            if (key != 'loginToken' and key != 'workoutId'):
                if (key == "title"):
                    cnnct_to_db.cursor.execute("UPDATE workout SET title=? WHERE id=?",[client_title,client_workoutId])
                elif (key == "completed"):
                    cur_date = datetime.datetime.now().strftime('%Y-%m-%d')
                    cnnct_to_db.cursor.execute("UPDATE workout SET completed=? AND completed_on=? WHERE id=?",[client_completed,cur_date,client_workoutId])
                else:
                    print("Error happened with inputs")

                if(cnnct_to_db.cursor.rowcount == 1):
                    cnnct_to_db.conn.commit()
                else:
                    return Response("Failed to update",
                                    mimetype="text/plain",
                                    status=400)
            else:
                continue
        cnnct_to_db.cursor.execute("SELECT * FROM workout WHERE id=?", [client_workoutId])
        updated_workout = cnnct_to_db.cursor.fetchone()
        cnnct_to_db.endConn()
        
        resp = {
            "workoutId" : updated_workout[0],
            "title" : updated_workout[1],
            "completed" : updated_workout[3]
        }

        return Response(json.dumps(resp),
                        mimetype="application/json",
                        status=200)
    except ConnectionError:
        cnnct_to_db.endConn()
        print("Error while attempting to connect to the database")
        return Response("Error while attempting to connect to the database",
                        mimetype="text/plain",
                        status=444)  
    except mariadb.DataError:
        cnnct_to_db.endConn()
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
    except mariadb.IntegrityError:
        cnnct_to_db.endConn()
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
def delete_workout():
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
        {   
            'name': 'workoutId',
            'datatype': int,
            'maxLength': 2,
            'required': True
        },
    ]

    try:
        check_data_required(requirements,data)
        validate_data(requirements,data)

    except RequiredDataNull:
        return Response("Missing required data in your input!",
                        mimetype="text/plain",
                        status=400)
    except TypeError:
        return Response("Incorrect datatype was used",
                        mimetype="text/plain",
                        status=400)
    except ValueError:
        return Response("Please check your inputs. An error was found with your data",
                        mimetype="text/plain",
                        status=400)
    except DataOutofBounds:
        return Response("Please check your inputs. Data is out of bounds",
                        mimetype="text/plain",
                        status=400)

    client_loginToken = data.get('loginToken')
    client_workoutId = data.get('workoutId')

    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        # Select the workoutId
        cnnct_to_db.cursor.execute("SELECT workout.id from user_session INNER JOIN user ON user_session.user_id = user.id INNER JOIN workout ON workout.user_id = user.id WHERE user_session.loginToken =? AND workout.id=?", [client_loginToken,client_workoutId])
        id_match = cnnct_to_db.cursor.fetchone()
        if id_match != None:
            id_match = id_match[0]
            cnnct_to_db.cursor.execute("DELETE FROM workout WHERE id=?",[id_match])
            if(cnnct_to_db.cursor.rowcount == 1):
                cnnct_to_db.conn.commit()
            else:
                return Response("Failed to update",
                                mimetype="text/plain",
                                status=400)
        else:
            raise ValueError
        
        cnnct_to_db.endConn()
        return Response("Sucessfully deleted workout",
                            mimetype="text/plain",
                            status=204)
    except ConnectionError:
        cnnct_to_db.endConn()
        print("Error while attempting to connect to the database")
        return Response("Error while attempting to connect to the database",
                        mimetype="text/plain",
                        status=444)
    except mariadb.DataError:
        cnnct_to_db.endConn()
        print("Something wrong with your data")
        return Response("Something wrong with your data",
                        mimetype="text/plain",
                        status=400)
    except ValueError:
        cnnct_to_db.endConn()
        print("No existing loginToken was found")
        return Response("Incorrect loginToken and password combination",
                        mimetype="text/plain",
                        status=400)

@app.route('/api/workouts', methods=['GET','POST','PATCH','DELETE'])
def workout_api():
    if (request.method == 'GET'):
        return get_workouts()
    elif (request.method == 'POST'):
        return post_workout()
    elif (request.method == 'PATCH'):
        return patch_workout()
    elif (request.method == 'DELETE'):
        return delete_workout()
    else:
        print("Something went wrong with the login API.")