from package import app
from flask import request, Response
import mariadb
import dbcreds
import json
import datetime
import bcrypt

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

def login_user():
    data = request.json
    requirements = [
        {   'name': 'email',
            'datatype': str,
            'maxLength': 50,
            'required': True
        },
        {   'name': 'password',
            'datatype': str,
            'maxLength': 50,
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
    
    client_email = data.get('email')
    client_password = data.get('password')

    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        cnnct_to_db.cursor.execute("SELECT password FROM user WHERE email=?",[client_email])
        matching_pw = cnnct_to_db.cursor.fetchone()
        matching_pw = matching_pw[0].encode()

        if (bcrypt.checkpw(client_password.encode(), matching_pw)):
            print("This is the correct password!")
        else:
            cnnct_to_db.endConn()
            return Response("Incorrect login combination",
                        mimetype="text/plain",
                        status=400)

        cnnct_to_db.cursor.execute("SELECT * FROM user WHERE email=?",[client_email])
        matching_info = cnnct_to_db.cursor.fetchone()
        client_id = matching_info[0]
        client_username = matching_info[1]
        client_email = matching_info[2]
            
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
        cur_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cnnct_to_db.cursor.execute("INSERT INTO user_session (loginToken,created_at,user_id) VALUES(?,?,?)",[generateUuid,cur_datetime,client_id])
        cnnct_to_db.conn.commit()

        cnnct_to_db.cursor.execute("SELECT loginToken FROM user_session  WHERE user_id =? ORDER BY id DESC LIMIT 1",[client_id])
        get_token = cnnct_to_db.cursor.fetchone()
        client_token = get_token[0]
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

    resp = {
        "userId": client_id,
        "email": client_email,
        "username": client_username,
        "loginToken": client_token,
    }
    return Response(json.dumps(resp),
                                mimetype="application/json",
                                status=201)

def logout_user():
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
    ]
    validate_data(requirements,data)
    check_data_required(requirements,data)

    client_loginToken = data.get('loginToken')
    
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()

        cnnct_to_db.cursor.execute("SELECT loginToken FROM user_session WHERE loginToken=?",[client_loginToken])

        match = cnnct_to_db.cursor.fetchone()
        #Only returns one row, so only one combination is valid
        if match == None:
            return Response("Incorrect data was received",
                            mimetype="plain/text",
                            status=400)

        cnnct_to_db.cursor.execute("DELETE FROM user_session WHERE loginToken=?", [match[0]])
        cnnct_to_db.conn.commit()
        return Response("Logged out successfully",
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

@app.route('/api/login', methods=['POST', 'DELETE'])
def login_api():
    if (request.method == 'POST'):
        return login_user()
        
    elif (request.method == 'DELETE'):
        return logout_user()
    else:
        print("Something went wrong with the login API.")
