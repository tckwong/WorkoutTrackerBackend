from package import app
import sys

#Debug / production environments
if (len(sys.argv) > 1):
    mode = sys.argv[1]
    if (mode == "production"):
        import bjoern
        host = '0.0.0.0'
        port = 5000
        print("Server is running in production mode")
        bjoern.run(app, host, port)
    elif (mode == "testing"):
        from flask_cors import CORS
        CORS(app)
        print("Server is running in testing mode")
        app.run(debug=True)
        #Should not have CORS open in production
    else:
        print("Invalid mode arugement, exiting")
        exit()
else:
    print ("No argument was provided")
    exit()
