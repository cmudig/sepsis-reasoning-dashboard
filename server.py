from flask import Flask, render_template, send_from_directory, request, redirect, jsonify
from blueprints.user import User
from flask_login import LoginManager, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
from google.cloud import storage
import os
import json
import gzip
import traceback
import random

# If in production mode, enable authentication
PRODUCTION_MODE = os.environ.get("PRODUCTION_MODE") == "1"
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "client", "dist")

BUCKET_NAME = "sepsis-challenging-cases"
BUCKET_DIRECTORIES = [
    "states"
]

# Initialize GCS client
storage_client = storage.Client()

# get metadata
with storage_client.bucket(BUCKET_NAME).blob('meta.json').open('r') as f:
    metadata = json.load(f)

app = Flask(__name__, template_folder=FRONTEND_BUILD_DIR)
csrf = CSRFProtect(app)

app.config['LOGIN_DISABLED'] = (os.environ.get("LOGIN_DISABLED") == "1" or not PRODUCTION_MODE)

# Read secret key from secret.txt if available, otherwise fallback (dev only)
if os.path.exists("secret.txt"):
    with open("secret.txt", "r") as file:
        app.secret_key = file.read().strip()
else:
    print("WARNING: Using the development secret key. If using in production, please make sure a secret.txt file is present.")
    app.secret_key = "efd06fa9d66fbdc84025a05066bc85d337e1c89a9cbff62ab4cf6fc6c5077f50"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/login"

# Path for our main Svelte page
@app.route("/")
@login_required
def base():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.authenticate(user_id, password)
        if user:
            login_user(user, remember=remember)
            return redirect("/")
        else:
            return render_template('login.html', template_params='The user ID and password you entered are invalid.')
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template('login.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    if path in ("global.css", "favicon.png") or path.startswith("assets/"):
        # These files are only in public
        return send_from_directory("client/dist", path)
    return send_from_directory(FRONTEND_BUILD_DIR, path)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/patient/<id>', methods=['GET'])
def get_patient_files(id):
    result = {'data': {}}
    for directory in BUCKET_DIRECTORIES:
        # Construct the GCS file path
        file_name = f"{directory}/{id}.json.gz"
        
        try:
            # Get the bucket and blob
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(file_name)
            
            if not blob.exists():
                # If the file doesn't exist, return a 404
                return f"Patient {file_name} not found.", 404
            
            # Download and decompress the file
            compressed_data = blob.download_as_bytes()
            uncompressed_data = gzip.decompress(compressed_data)
            
            # Load the JSON content
            json_content = json.loads(uncompressed_data)
            if "num_timesteps" in json_content:
                result.update({k: v for k, v in json_content.items() if k != 'data'})
                result['data'].update(json_content['data'])
            else:
                result['data'].update(json_content['data'])
        
        except Exception as e:
            # Handle any unexpected errors
            traceback.print_exc()
            return str(e), 400
    return jsonify(result)

@app.route('/patient/random', methods=['GET'])
def random_patient():
    random_id = random.choice(metadata['patient_ids'])
    return redirect(f"/patient/{random_id}")

if __name__ == "__main__":
    app.run(debug=True, port=4999)
