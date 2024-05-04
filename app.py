from flask import render_template
from flask_cors import CORS
from src import create_app
import os
from flask_mail import Mail

app = create_app()

# Retrieve secret key variable from heroku server
app.secret_key = os.environ.get('SECRET_KEY')

# Initialize cors to allow all origins for testing api in development
CORS(app)
# TODO: # Configure CORS with specific allowed origins for security
# cors = CORS(app, origins=["http://localhost:3000", "https://piyata.tech"])

app.secret_key = os.environ.get('SECRET_KEY')
app.config['MAIL_SERVER'] = os.environ.get("MAIL_SERVER")
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")

mail = Mail(app)


@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)