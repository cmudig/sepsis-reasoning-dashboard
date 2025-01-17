# Sepsis RST Viewer

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