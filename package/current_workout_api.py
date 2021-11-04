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

def get_cur_workout():
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
    except ConnectionError:
        cnnct_to_db.endConn()
        return Response("Error while attempting to connect to the database",
                                    mimetype="text/plain",
                                    status=400)

    params_id = request.args.get("workoutId")

    if (params_id is None):
        return Response(json.dumps("Please provide a 'workoutId'"),
                                mimetype="text/plain",
                                status=400)

    elif (params_id is not None):
        try:
            params_id = int(request.args.get("workoutId"))
        except ValueError:
            cnnct_to_db.endConn()
            return Response("Incorrect datatype received",
                                        mimetype="text/plain",
                                        status=400)
    
        if ((0< params_id<9999999)):
            cnnct_to_db.cursor.execute("SELECT * FROM exercise INNER JOIN workout ON exercise.workout_id = workout.id WHERE workout.id =?", [params_id])
            cur_workout_data = cnnct_to_db.cursor.fetchall()
            list = []
            content = {}
            for result in cur_workout_data:
                content = { 
                        'workoutId': result[5],
                        'exerciseId': result[0],
                        'workoutTitle' : result[9],
                        'exerciseName' : result[1],
                        'reps' : result[2],
                        'sets' : result[3],
                        'weight' : result[4],
                        'created_on': result[10]
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

def post_current_workout():
    data = request.json
    # data is array object of dictionaries
    print(data)
    client_loginToken = data[0].get('loginToken')
    # client_userId = data[0].get('userId')
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()

        #check loginToken exists and is logged in
        cnnct_to_db.cursor.execute("SELECT user_id FROM user_session WHERE user_session.loginToken =?", [client_loginToken])
        session_match = cnnct_to_db.cursor.fetchone()
        #check for a row match check if user is loggeds in
        if session_match == None:
            return Response("No matching results were found",
                                mimetype="text/plain",
                                status=400)
        db_userId = session_match[0]
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #1. First, update existing workout template
        # cnnct_to_db.cursor.execute("SELECT exercise_name FROM exercise INNER JOIN workout ON workout_id = workout.id WHERE workout.id=?",[data[0].get('workoutId')])
        # all_exercises = cnnct_to_db.cursor.fetchall()
        # # First check if an exercise already exists in DB for selected workoutId
        # list_all_exercises=[]
        # for i in all_exercises:
        #     list_all_exercises.append(i[0])
        # newllst= [dict['exerciseName'] for dict in data]
        # duplicates = [item in list_all_exercises for item in newllst]

        # for index in range(len(duplicates)):
        #     if (duplicates[index] == True):
        #         continue
        #     else:
        #         cnnct_to_db.cursor.execute("INSERT INTO exercise(exercise_name,reps,sets,weight,workout_id,completed,user_id) VALUES(?,?,?,?,?,?,?)",[data[index].get('exerciseName'),data[index].get('reps'),data[index].get('sets'),data[index].get('weight'),data[index].get('workoutId'),0,db_userId])
        #         if(cnnct_to_db.cursor.rowcount == 1):
        #             cnnct_to_db.conn.commit()
        #         else:
        #             return Response("Failed to add workout",
        #                                 mimetype="text/plain",
        #                                 status=400)
        
    
        #2. Update completed workout table and exercise tables
        #get current time
        session_cur_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cnnct_to_db.cursor.execute("INSERT INTO completed_workouts(title,completed_at,user_id) VALUES(?,?,?)",[data[0].get('title'),session_cur_datetime,db_userId])
        if(cnnct_to_db.cursor.rowcount == 1):
                cnnct_to_db.conn.commit()
        else:
            return Response("Failed to update",
                            mimetype="text/plain",
                            status=400)
        #Fetch completed_workoutId
        cnnct_to_db.cursor.execute("SELECT LAST_INSERT_ID();")
        completed_workout_id = cnnct_to_db.cursor.fetchone()
        
        index=0
        for index in range(len(data)):
            
            cnnct_to_db.cursor.execute("INSERT INTO completed_exercises(exercise_name,reps,sets,weight,completed_workout_id,user_id) VALUES(?,?,?,?,?,?)",[data[index].get('exerciseName'),data[index].get('reps'),data[index].get('sets'),data[index].get('weight'),completed_workout_id[0],db_userId])
            if(cnnct_to_db.cursor.rowcount == 1):
                    cnnct_to_db.conn.commit()
            else:
                return Response("Failed to update",
                                mimetype="text/plain",
                                status=400)
        
        #Send a response to front-end
        # cnnct_to_db.cursor.execute("SELECT completed_workouts.id,exercise_name,reps,sets,weight,workout_id,completed_exercises.user_id, exercise.completed FROM completed_exercises INNER JOIN completed_workouts ON completed_workout_id = completed_workouts.id WHERE completed_workouts.id=?",[completed_workout_id])
        # all_exercises_data = cnnct_to_db.cursor.fetchall()
        # exercise_list = []
        # content = {}
        # for result in all_exercises_data:
        #     content = {
        #             "workoutId" : result[0],
        #             "exerciseName" : result[1],
        #             "reps" : result[2],
        #             "sets" : result[3],
        #             "weight" : result[4],
        #             "workoutId" : result[5],
        #             "userId" : result[6],
                    
        #     }
        #     exercise_list.append(content)
        return Response("Workout completed",
                                mimetype="text/plain",
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


# def patch_workout():
#     data = request.json
#     requirements = [
#         {   'name': 'loginToken',
#             'datatype': str,
#             'maxLength': 32,
#             'required': True
#         },
#         {   
#             'name': 'workoutId',
#             'datatype': int,
#             'maxLength': 2,
#             'required': True
#         },
#         {   
#             'name': 'title',
#             'datatype': str,
#             'maxLength': 40,
#             'required': False
#         },
#         {
#             'name': 'completed',
#             'datatype': int,
#             'maxLength': 1,
#             'required': False
#         }
#     ]
#     # "validate_data(requirements,data)
#     # check_data_required(requirements,data)"

#     client_loginToken = data.get('loginToken')
#     client_workoutId = data.get('workoutId')
#     client_title = data.get('title')
#     client_completed = data.get('completed')
    
#     try:
#         cnnct_to_db = MariaDbConnection()
#         cnnct_to_db.connect()
#         #Check for workout ownership
#         cnnct_to_db.cursor.execute("SELECT user.id,title,created_on,completed,completed_on from user_session INNER JOIN user ON user_session.user_id = user.id INNER JOIN workout ON workout.user_id = user.id WHERE user_session.loginToken =? AND workout.id=?", [client_loginToken,client_workoutId])
#         info_match = cnnct_to_db.cursor.fetchone()
#         if not info_match:
#             cnnct_to_db.endConn()
#             return Response("No matching results were found",
#                                 mimetype="text/plain",
#                                 status=400)

#         for key in data:
#             if (key != 'loginToken' and key != 'workoutId'):
#                 if (key == "title"):
#                     cnnct_to_db.cursor.execute("UPDATE workout SET title=? WHERE id=?",[client_title,client_workoutId])
#                 elif (key == "completed"):
#                     cur_date = datetime.datetime.now().strftime('%Y-%m-%d')
#                     cnnct_to_db.cursor.execute("UPDATE workout SET completed=? AND completed_on=? WHERE id=?",[client_completed,cur_date,client_workoutId])
#                 else:
#                     print("Error happened with inputs")

#                 if(cnnct_to_db.cursor.rowcount == 1):
#                     cnnct_to_db.conn.commit()
#                 else:
#                     return Response("Failed to update",
#                                     mimetype="text/plain",
#                                     status=400)
#             else:
#                 continue
#         cnnct_to_db.cursor.execute("SELECT * FROM workout WHERE id=?", [client_workoutId])
#         updated_workout = cnnct_to_db.cursor.fetchone()
#         cnnct_to_db.endConn()
        
#         resp = {
#             "workoutId" : updated_workout[0],
#             "title" : updated_workout[1],
#             "completed" : updated_workout[3]
#         }

#         return Response(json.dumps(resp),
#                         mimetype="application/json",
#                         status=200)
#     except ConnectionError:
#         cnnct_to_db.endConn()
#         print("Error while attempting to connect to the database")
#         return Response("Error while attempting to connect to the database",
#                         mimetype="text/plain",
#                         status=444)  
#     except mariadb.DataError:
#         cnnct_to_db.endConn()
#         print("Something wrong with your data")
#         return Response("Something wrong with your data",
#                         mimetype="text/plain",
#                         status=400)
#     except mariadb.IntegrityError:
#         cnnct_to_db.endConn()
#         print("Something wrong with your data")
#         return Response("Something wrong with your data",
#                         mimetype="text/plain",
#                         status=400)

def delete_workout():

    #Exit current workout early. Remove workout-session. Delete from front-end
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

@app.route('/api/current-workout', methods=['GET','POST','PATCH','DELETE'])
def current_workout_api():
    if (request.method == 'GET'):
        return get_cur_workout()
    elif (request.method == 'POST'):
        return post_current_workout()
    elif (request.method == 'PATCH'):
        pass
    elif (request.method == 'DELETE'):
        pass
    else:
        print("Something went wrong with the login API.")