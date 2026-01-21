# Sepsis Reasoning Cue Dashboard

This repository demonstrates the model training, patient selection, and dashboard design for the CHI'26 paper "Intelligent Reasoning Cues: A Framework and Case Study of the Roles of AI Information in Complex Decisions".

![Screenshot of the reasoning cue dashboard, with a callout for the patient vignettes.](/assets/study-interface.png)

## Setup Instructions

To set up, `cd` into the main repository directory, and run
`pip install -r requirements.txt`. Then `cd` into the `client` directory and run
`npm install && npm run build`.

Make sure you have a service account key JSON file that can access the GCS bucket,
and set the environment variable like so: 

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

Run `python -m server` to start the Flask server.

## Model Training and Upload

The `sepsis_models` directory shows how the autoencoder was trained to produce the reasoning cues in our study. See the `load_reasoning_cues.ipynb` notebook for the full source code. (Please note that this script requires a custom preprocessed version of MIMIC-IV to work; please contact [the authors](mailto:venkats@cmu.edu) if you would like to run this code as-is.)

## Setting Up Study Protocol

Upload the study protocol JSON to the GCS bucket in a file named `study_protocol.json`. The study protocol used in our work is at the top level of this repository.

Participant accounts can be set up locally by running `python blueprints/users.py`.