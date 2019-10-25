from flask import Flask 
from flask import url_for


app = Flask(__name__)
@app.route('/') 
def hello():    
    return 'Welcome to My Watchlist!'
