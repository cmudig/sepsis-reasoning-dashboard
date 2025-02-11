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

## To set up study protocol

Upload the study protocol JSON to the GCS bucket in a file named `study_protocol.json`.
Example of the study protocol format here:

```json
{
  "text": {
    "intro_text": "Thank you for participating in this study about decision-making on patients with suspected sepsis.\n\nImagine you are working an ICU shift, and you are reviewing information about patients currently in the ICU before presenting them in morning rounds. Your task will be to recommend the next steps for each patient in terms of their hemodynamic management. Please think aloud as you reason about the case.",
    "post_patient_items": [
      {
        "question": "How challenging was this case?",
        "answer_instruction": "Answer on a scale from 1-10, with 1 being extremely easy and 10 being extremely challenging."
      },
      {
        "question": "How confident are you in your decision",
        "answer_instruction": "Answer on a scale from 1-10, with 1 being not at all confident and 10 being extremely confident."
      },
      {
        "question": "How useful was the information provided by Sepsis AI for this case?",
        "answer_instruction": "Answer on a scale from 1-10, with 1 being not at all useful and 10 being extremely useful."
      }
    ],
    "prompt_text": "What is your recommendation for the next steps for this patient in terms of hemodynamic management?"
  },
  "participant_ids": ["p1", "p2", "p3", "p4"],
  "patients": [
    {
      "id": 30327685,
      "dataset": "weighted",
      "ts": 0,
      "ads_ids": [
        "descriptive",
        "predictive_vaso_independent",
        "predictive_vaso_dependent",
        "predictive_morta_independent",
        "predictive_morta_dependent",
        "prescriptive_peer",
        "prescriptive_outcome"
      ],
      "pseudonym": "Sandra Gonzalez",
      "vignette": "Mrs. Gonzalez is a 68-year-old woman. She was just admitted to the ICU and is intubated and sedated."
    },
    {
      "id": 34030023,
      "dataset": "weighted",
      "ts": 34,
      "ads_ids": [
        "descriptive",
        "predictive_vaso_independent",
        "predictive_vaso_dependent",
        "predictive_morta_independent",
        "predictive_morta_dependent"
      ],
      "pseudonym": "Edwin Murphy",
      "vignette": "Mr. Murphy is a 44-year-old man with a history of asthma, HTN, macrocytic anemia, PE/DVT, erosive gastritis, alcoholism, and prior bouts of alcohol-induced pancreatitis, transferred to the ICU for shock, likely secondary to severe pancreatitis."
    },
    {
      "id": 30052347,
      "dataset": "weighted",
      "ts": 27,
      "ads_ids": [
        "predictive_morta_independent",
        "predictive_morta_dependent",
        "prescriptive_peer",
        "prescriptive_outcome"
      ],
      "pseudonym": "Richard Lewis",
      "vignette": "Mr. Lewis is a 92-year-old man with anoxic brain injury, ventilator-dependent who presented initially with respiratory failure, bilateral pneumonia, status post 14-day antibiotics course with respiratory status at baseline, course complicated by renal failure, with decreasing hematocrit likely secondary to chronic GI bleed and anemia of chronic disease, funguria status post foley change, with worsening uremia."
    },
    {
      "dataset": "weighted",
      "id": 31961399,
      "ts": 2,
      "ads_ids": [
        "descriptive",
        "predictive_vaso_independent",
        "predictive_vaso_dependent",
        "prescriptive_peer",
        "prescriptive_outcome"
      ],
      "pseudonym": "Isaiah Johnston",
      "vignette": "Mr. Johnston is a 27-year-old man, recently admitted to the Trauma service and taken immediately to the operating room for exploratory laparotomy, small-bowel resection, resection of transverse colon, and right femoral line arterial line placement."
    }
  ]
}
```

The `participant_ids` file should contain user IDs that will be used to log in
each participant. They should be set up locally by running `python blueprints/users.py`.