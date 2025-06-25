from flask import Flask, render_template, send_from_directory, request, redirect, jsonify
from blueprints.user import User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from google.cloud import storage
import os
import json
import gzip
import traceback
import random
import numpy as np

# If in production mode, enable authentication
PRODUCTION_MODE = os.environ.get("PRODUCTION_MODE") == "1"
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "client", "dist")

BUCKET_NAME = "sepsis-challenging-cases"
BUCKET_DIRECTORIES = [
    "states",
    "descriptive",
    "predictive_vaso_independent",
    "predictive_vaso_dependent",
    "predictive_morta_independent",
    "predictive_morta_dependent",
    "prescriptive_peer",
    "prescriptive_outcome"
]

# Initialize GCS client
storage_client = storage.Client()

metadata = {}

with storage_client.bucket(BUCKET_NAME).blob('meta.json').open('r') as f:
    datasets = json.load(f)['datasets']

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

@app.route("/study")
@login_required
def study():
    return render_template('study.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.authenticate(user_id, password)
        if user:
            login_user(user, remember=remember)
            if 'next' in request.form and request.form.get('next').startswith('/'):
                return redirect(request.form.get('next'))
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
    if not app.config['LOGIN_DISABLED'] and not current_user.is_authenticated:
        return redirect("/login")
    return send_from_directory(FRONTEND_BUILD_DIR, path)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/dataset', methods=['GET'])
def get_datasets():
    if not app.config['LOGIN_DISABLED'] and not current_user.is_authenticated: return "Not authenticated", 403
    return jsonify(datasets)

@app.route('/dataset/<dataset_name>/patient/<id>', methods=['GET'])
def get_patient_files(dataset_name, id):
    if not app.config['LOGIN_DISABLED'] and not current_user.is_authenticated: return "Not authenticated", 403
    result = {'data': {}}
    for directory in BUCKET_DIRECTORIES:
        # Construct the GCS file path
        file_name = f"{dataset_name}/{directory}/{id}.json.gz"
        
        try:
            # Get the bucket and blob
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(file_name)
            
            if not blob.exists():
                # If the file doesn't exist, return a 404
                if directory == "states":
                    return f"Patient {file_name} not found.", 404
                else:
                    continue
            print("Found directory", directory, 'for', id)
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

@app.route('/dataset/<dataset_name>/patient/random', methods=['GET'])
def random_patient(dataset_name):
    if not app.config['LOGIN_DISABLED'] and not current_user.is_authenticated: return "Not authenticated", 403
    global metadata
    if dataset_name not in metadata:
        # get metadata
        with storage_client.bucket(BUCKET_NAME).blob(f'{dataset_name}/meta.json').open('r') as f:
            metadata[dataset_name] = json.load(f)

    random_id = random.choice(metadata[dataset_name]['patient_ids'])
    return redirect(f"/dataset/{dataset_name}/patient/{random_id}")

def make_participant_assignments(ads_ids, num_ads=7, max_per_ads=2, num_to_generate=48):
    """
    Each element of ads_ids should be a list of IDs corresponding to ADS
    interfaces that have interesting outputs for that patient.
    """

    min_per_patient = (num_ads * 2) // len(ads_ids)
    unique_ids = set(id for p in ads_ids for id in p)

    np.random.seed(1234)
    random.seed(1234)
    
    reduced_ads_ids = [[id for id in p] for p in ads_ids]
    for ads_id in unique_ids:
        while sum(sum(id == ads_id for id in p) for p in reduced_ads_ids) > max_per_ads:
            idx_to_remove = np.random.choice([i for i in range(len(reduced_ads_ids))
                                            if ads_id in reduced_ads_ids[i] and
                                            len(reduced_ads_ids[i]) > min_per_patient])
            reduced_ads_ids[idx_to_remove].remove(ads_id)
    
    # shuffle the ids
    while any(len(set(p[i] for p in reduced_ads_ids if i < len(p))) < 
          len(list(p[i] for p in reduced_ads_ids if i < len(p))) 
          for i in range(max(len(p) for p in reduced_ads_ids))):
        reduced_ads_ids = [np.random.permutation(p).tolist() for p in reduced_ads_ids]
    
    ordering = []
    no_ai_index = 0
    for pid in range(num_to_generate):
        participant_conditions = [None, None, None, None]
        for i, current in enumerate(participant_conditions):
            if i == no_ai_index: participant_conditions[i] = "none"
            else:
                # find the first element in the list that has the smallest count so far
                ads_counts = [(id, sum((i, id) in o for o in ordering)) for id in reduced_ads_ids[i]]
                min_count = min(ads_counts, key=lambda x: x[1])[1]
                for option, count in ads_counts:
                    if count == min_count and option not in participant_conditions:
                        participant_conditions[i] = option
                        break
                        
        no_ai_index = (no_ai_index + 1) % len(ads_ids)
        numbered_conditions = list(enumerate(participant_conditions))
        random.shuffle(numbered_conditions)
        ordering.append(numbered_conditions)

    print(ordering)
    print("Counts of conditions:")
    for condition in unique_ids:
        print(condition, [sum((i, condition) in x for x in ordering) for i in range(len(ads_ids))])
        
    return [{"conditions": [{'patient': i, 'ads': c} for i, c in conditions]}
            for conditions in ordering]

@app.route('/study_protocol', methods=['GET'])
def get_study_protocol():    
    if not app.config['LOGIN_DISABLED'] and not current_user.is_authenticated: return "Not authenticated", 403
    with storage_client.bucket(BUCKET_NAME).blob(f'study_protocol.json').open('r') as f:
        study_protocol = json.load(f)
    condition_ordering_path = storage_client.bucket(BUCKET_NAME).blob(f'condition_ordering.json')
    if not condition_ordering_path.exists():
        condition_ordering = make_participant_assignments([p["ads_ids"] for p in study_protocol["patients"]])
        with condition_ordering_path.open('w') as f:
            json.dump(condition_ordering, f)
    else:
        with condition_ordering_path.open('r') as f:
            condition_ordering = json.load(f)
    
    if current_user.is_authenticated:
        user_id = current_user.get_id()
        print("User ID:", user_id)
        if user_id in study_protocol["participant_ids"]:
            participant_id = study_protocol["participant_ids"].index(user_id)
            print("participantID:", participant_id)
            # if participant_id == -1:
            #     return "Invalid participant ID", 400
        else:
            participant_id = 0
            user_id = 'test'
    else:
        user_id = 'test'
        participant_id = 0
                
    conditions = condition_ordering[participant_id]["conditions"]
    return jsonify({
        "text": study_protocol["text"],
        "patients": [{
            **{k: v for k, v in study_protocol["patients"][condition['patient']].items() if k != "ads_ids"},
            "ads": condition['ads']
        } for condition in conditions],
        "dev_mode": user_id == 'test'
    })
    
    
if __name__ == "__main__":
    app.run(debug=True, port=4999)
