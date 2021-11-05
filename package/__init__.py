from flask import Flask
app = Flask(__name__)

import package.login_api
import package.user_api
import package.workout_api
import package.exercise_api
import package.current_workout_api
import package.workout_session_api
import package.workout_history_api


