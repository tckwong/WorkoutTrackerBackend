from flask import request, Response
import mariadb
import json
import dbcreds
from package import app
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
        raise RequiredDataNull

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
                raise TypeError

            #Check for max char length
            maxLen = mydict[found_index]['maxLength']
            if(type(data.get(item)) == str and maxLen != None):
                if(len(data.get(item)) > maxLen):
                    raise DataOutofBounds
        else:
            raise ValueError

def get_users():
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
        cnnct_to_db.cursor.execute("SELECT * FROM user")
        list = cnnct_to_db.cursor.fetchall()
        user_list = []
        content = {}
        for result in list:
            content = { 'userId': result[0],
                        'username': result[1],
                        'email' : result[2],
                        }
            user_list.append(content)

        cnnct_to_db.endConn()
        return Response(json.dumps(user_list),
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
    
        if ((0< params_id<99999999)):
            cnnct_to_db.cursor.execute("SELECT * FROM user WHERE id =?", [params_id])
            userIdMatch = cnnct_to_db.cursor.fetchall()
            user_list = []
            content = {}
            for result in userIdMatch:
                content = { 'userId': result[0],
                        'username': result[1],
                        'email' : result[2],
                        }
            user_list.append(content)
            cnnct_to_db.endConn()
        else:
            cnnct_to_db.endConn()
            return Response("Invalid parameters. ID Must be an integer",
                                    mimetype="text/plain",
                                    status=400)

        return Response(json.dumps(user_list),
                                    mimetype="application/json",
                                    status=200)

def create_new_user():
    data = request.json
    
    requirements = [
        {   'name': 'username',
            'datatype': str,
            'maxLength': 50,
            'required': True
        },
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
    client_username = data.get('username')
    client_password = data.get('password')

    # Salt and hash password before inserting into DB
    salt_pw = bcrypt.gensalt()
    hashed_client_password = bcrypt.hashpw(client_password.encode(), salt_pw)
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        cnnct_to_db.cursor.execute("INSERT INTO user(email, username, password) VALUES(?,?,?);",[client_email,client_username,hashed_client_password])
        if(cnnct_to_db.cursor.rowcount == 1):
            cnnct_to_db.conn.commit()
        else:
            return Response("Failed to update",
                                mimetype="text/plain",
                                status=400)
        cnnct_to_db.cursor.execute("SELECT LAST_INSERT_ID();")
        get_userId = cnnct_to_db.cursor.fetchone()

        resp = {
        "userId": get_userId[0],
        "email": client_email,
        "username": client_username
        }
        return Response(json.dumps(resp),
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

def update_user_info():
    data = request.json

    requirements = [
            {   'name': 'loginToken',
                'datatype': str,
                'maxLength': 32,
                'required': True
            },  
            {   'name': 'username',
                'datatype': str,
                'maxLength': 50,
                'required': False
            },
            {   'name': 'email',
                'datatype': str,
                'maxLength': 50,
                'required': False
            },
            {   'name': 'password',
                'datatype': str,
                'maxLength': 50,
                'required': False
        },
    ]

    try:
        check_data_required(requirements,data)
    except RequiredDataNull:
        return Response("Missing required data in your input!",
                        mimetype="text/plain",
                        status=400)
    try:
        validate_data(requirements,data)
    except TypeError:
        return Response("Incorrect datatype was used",
                        mimetype="text/plain",
                        status=400)
    except ValueError:
        return Response("Please check your inputs. An error was found with your data",
                        mimetype="text/plain",
                        status=400)
    
    client_loginToken = data.get('loginToken')
    
    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        cnnct_to_db.cursor.execute("SELECT user.id FROM user INNER JOIN user_session ON user_session.user_id = user.id WHERE user_session.loginToken =?", [client_loginToken])
        id_match = cnnct_to_db.cursor.fetchone()
        # Check if a matching user + loginToken was found. Return error if nothing was found
        if id_match == None:
            cnnct_to_db.endConn()
            return Response("Please check your inputs. No matching user / loginToken combination",
                        mimetype="text/plain",
                        status=400)
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
    try:
        for key in data:
            result = data[key]
            if (key != 'loginToken'):
                if (key == "email"):
                    cnnct_to_db.cursor.execute("UPDATE user SET email =? WHERE user.id=?",[result,id_match[0]])
                elif (key == "username"):
                    cnnct_to_db.cursor.execute("UPDATE user SET username =? WHERE user.id=?",[result,id_match[0]])
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
        
        cnnct_to_db.cursor.execute("SELECT * FROM user WHERE id=?", [id_match[0]])
        updated_user = cnnct_to_db.cursor.fetchone()
        
        resp =  {'userId': updated_user[0],
                'username': updated_user[1],
                'email' : updated_user[3],
                }
        cnnct_to_db.endConn()
        return Response(json.dumps(resp),
                        mimetype="application/json",
                        status=200)
    except ConnectionError:
        cnnct_to_db.endConn()
        return Response("Error while attempting to connect to the database",
                                    mimetype="text/plain",
                                    status=400)
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

def delete_user():                    
    data = request.json
    requirements = [
        {   'name': 'loginToken',
            'datatype': str,
            'maxLength': 32,
            'required': True
        },
        {   
            'name': 'password',
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

    client_loginToken = data.get('loginToken')
    client_password = data.get('password')

    #Salt + hash password input
    salt_pw = bcrypt.gensalt()
    hashed_client_password = bcrypt.hashpw(client_password.encode(), salt_pw)

    try:
        cnnct_to_db = MariaDbConnection()
        cnnct_to_db.connect()
        #checks password and logintoken are in the same row
        cnnct_to_db.cursor.execute("SELECT user.id FROM user INNER JOIN user_session ON user_session.user_id = user.id WHERE user.password =? and user_session.loginToken =?",[hashed_client_password, client_loginToken])
        id_match = cnnct_to_db.cursor.fetchone()
        if id_match != None:
            id_match = id_match[0]
            cnnct_to_db.cursor.execute("DELETE FROM user WHERE id=?",[id_match])
            if(cnnct_to_db.cursor.rowcount == 1):
                print("User deleted sucessfully")
                cnnct_to_db.conn.commit()
            else:
                return Response("Failed to update",
                                mimetype="text/plain",
                                status=400)
        else:
            raise ValueError
        
        cnnct_to_db.endConn()
        return Response("Sucessfully deleted user",
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
        print("Incorrect loginToken and password combination")
        return Response("Incorrect loginToken and password combination",
                        mimetype="text/plain",
                        status=400)

@app.route('/api/users', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def users_api():
    if (request.method == 'GET'):
        return get_users()
    elif (request.method == 'POST'):
        return create_new_user()    
    elif (request.method == 'PATCH'):
        return update_user_info()
    elif (request.method == 'DELETE'):
        return delete_user()
    else:
        print("Something went wrong.")