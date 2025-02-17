import pandas as pd
import numpy as np

NORMAL_RANGES = {
    "Lactic Acid": { "min": 0.5, "max": 1.6 },
    "Troponin": { "max": 1 }, # not sure what these units are
    "PTT": { "min": 60, "max": 70 },
    "PT": { "min": 11, "max": 13.5 },
    "INR": { "min": 0.8, "max": 1.1 },
    "Arterial pH": { "min": 7.35, "max": 7.45 },
    "Arterial BE": { "min": -4, "max": 2 },
    "PaO2": { "min": 75, "max": 100 },
    "PaCO2": { "min": 35, "max": 45 },
    "Bicarbonate": { "min": 20, "max": 32 },
    "WBC Count": { "min": 4.5, "max": 11 },
    "Hemoglobin": { "male": { "min": 14.0, "max": 17.5 },
                    "female": { "min": 12.3, "max": 15.3 }},
    "Hematocrit": { "male": { "min": 41, "max": 50 },
                    "female": { "min": 36, "max": 48 }},
    "Platelet Count": { "min": 130, "max": 400 },
    "AST": { "female": { "min": 9, "max": 25 }, "male": { "min": 10, "max": 40 } },
    "ALT": { "female": { "min": 7, "max": 30 }, "male": { "min": 10, "max": 55 } },
    "Total Bili": { "min": -1, "max": 5 },
    "Direct Bili": { "min": -1, "max": 2 },
    "Potassium": { "min": 3.4, "max": 5 },
    "Sodium": { "min": 135, "max": 145 },
    "Chloride": { "min": 95, "max": 108 },
    "Glucose": { "min": 110, "max": 180 },
    "BUN": { "min": 8, "max": 25 },
    "Creatinine": {
        "female": { "min": 0.6, "max": 1.8 },
        "male": { "min": 0.8, "max": 2.4 },
      },
    "Ionized Ca": { "min": 1.1, "max": 1.4 },
    "GCS Eye Opening": { "min": 3, "max": 6 },
    "GCS Motor Response": { "min": 3, "max": 7 },
    "GCS Verbal Response": { "min": 3, "max": 6 },
    "RASS": { "min": -3, "max": 2 }
}

state_features = [
    {
        "name": "Summary",
        "expanded": True,
        "children": [
            { "name": "Heart Rate", "unit": "bpm" }, 
            "Heart Rhythm", 
            { "name": "mAP", "unit": "mmHg" }, 
            { "name": "Temperature", "col": "Temperature C", "unit": "º C" }, 
            "Invasive Ventilation", 
            "Immunosuppressant",
            "Dialysis",
            { "name": "Positive Culture",
              "list_positive": {
                  "Positive Blood Culture": "Blood",
                  "Positive Urine Culture": "Urine",
                  "Positive Stool Culture": "Stool",
                  "Positive Swab Culture": "Swab",
                  "Positive Tissue Culture": "Tissue",
                  "Positive Sputum Culture": "Sputum",
              }
            },
            "Antimicrobial",
            { "name": "Fluid Balance", "unit": "ml" },
            { "name": "Vasopressors",
              "list_positive": {
                  "vaso_Dopamine": "Dopamine",
                  "vaso_Epinephrine": "Epinephrine",
                  "vaso_Norepinephrine": "Norepinephrine",
                  "vaso_Phenylephrine": "Phenylephrine",
                  "vaso_Vasopressin": "Vasopressin",
              }
            }
        ]
    },
    {
        "name": "Vitals",
        "children": [
            { "name": "Heart Rate", "unit": "bpm" }, 
            "Heart Rhythm", 
            { "name": "BP Systolic", "col": "SysBP", "unit": "mmHg" }, 
            { "name": "BP Diastolic", "col": "DiaBP", "unit": "mmHg" } ,
            { "name": "mAP", "unit": "mmHg" }, 
            "CVP", 
            { "name": "Temperature", "col": "Temperature C", "unit": "º C" }, 
            { "name": "PAPmean", "exclude_missing": True }, 
        ]
    },
    {
        "name": "Labs",
        "children": [
            {
                "name": "Chemistries",
                "children": [            
                    "Sodium", 
                    "Potassium", 
                    "Chloride", 
                    "Bicarbonate", 
                    "Glucose", 
                    "Calcium", 
                    "Ionized Ca", 
                    "Magnesium"
            ]},
            {
                "name": "CBC",
                "children": [
                    "WBC Count", 
                    "Hemoglobin", 
                    "Hematocrit", 
                    "Platelet Count"
            ]},
            {
                "name": "Coags",
                "children": [
                    "PTT", 
                    "PT", 
                    "INR"
            ]},
            {
                "name": "ABG",
                "children": [
                    "Arterial pH", 
                    "Arterial BE", 
                    "PaO2", 
                    "PaCO2", 
                    "Venous O2 Sat"
                ]
            }
        ]
    },
    {
        "name": "Renal",
        "children": [
            "Dialysis",
            "BUN",
            "Creatinine"
        ]
    },
    {
        "name": "Liver",
        "children": [
            "AST", 
            "ALT", 
            "Total Bili", 
            "Direct Bili"
    ]},
    {
        "name": "Cardiac",
        "children": [
            "Heart Rhythm", 
            "Cardioversion/Defibrillation", 
            "Lactic Acid", 
            "Troponin"
    ]},
    {
        "name": "Neuro",
        "children": [
            "RASS", 
            "GCS",
        ]
    },
    {
        "name": "Respiratory",
        "children": [
            "Invasive Ventilation", 
            "Non-invasive Ventilation", 
            "O2 Delivery Device", 
            {
                "name": "Vent Settings",
                "children": [
                    { "name": "Tidal Volume", "exclude_missing": True }, 
                    { "name": "Respiratory Rate", "exclude_missing": True }, 
                    { "name": "PEEP", "exclude_missing": True }, 
                    { "name": "FiO2", "exclude_missing": True }, 
                    { "name": "SpO2", "exclude_missing": True }, 
                    { "name": "Minute Volume", "exclude_missing": True }, 
                    { "name": "Plateau Pressure", "exclude_missing": True }, 
                    { "name": "Peak Inspiratory Pressure", "exclude_missing": True }, 
                    { "name": "Mean Airway Pressure", "exclude_missing": True }, 
                ]
            },
        ]
    },
    {
        "name": "Infectious Disease",
        "children": [
            { "name": "Positive Culture",
              "list_positive": {
                  "Positive Blood Culture": "Blood",
                  "Positive Urine Culture": "Urine",
                  "Positive Stool Culture": "Stool",
                  "Positive Swab Culture": "Swab",
                  "Positive Tissue Culture": "Tissue",
                  "Positive Sputum Culture": "Sputum",
              }
            },
            "Antimicrobial", 
        ]
    },
    {
        "name": "Hemodynamics",
        "children": [
            { "name": "Fluid Balance", "unit": "ml" },
            {
                "name": "Fluids",
                "children": [
                    { "name": "Fluids Last 4 h", "unit": "ml" },
                    { "name": "Fluid Type",
                      "list_positive": {
                          "Fluid_Isotonic Crystalloid": "Isotonic Crystalloid",
                          "Fluid_Hypertonic Crystalloid": "Hypertonic Crystalloid",
                          "Fluid_Hypotonic Crystalloid": "Hypotonic Crystalloid",
                          "Fluid_Isotonic Colloid": "Isotonic Colloid",
                          "Fluid_Blood Products": "Blood Products",
                      }
                    },
                    { "name": "Fluids Last 24 h", "unit": "ml" }
                ]
            },
            {
                "name": "Outputs",
                "children": [
                    "Diuretic", 
                    { "name": "Urine Last 24 h", "unit": "ml" }, 
                    { "name": "Non-Urine Fluid", "unit": "ml", "exclude_missing": True }, 
                ]
            },
            {
                "name": "Vasopressors",
                "children": [
                    { "name": "Vasopressor", "unit": "mcg/kg/min" },
                    { "name": "Vasopressor Type",
                      "list_positive": {
                          "vaso_Dopamine": "Dopamine",
                          "vaso_Epinephrine": "Epinephrine",
                          "vaso_Norepinephrine": "Norepinephrine",
                          "vaso_Phenylephrine": "Phenylephrine",
                          "vaso_Vasopressin": "Vasopressin",
                      }
                    }
                ]
            }
        ]
    },
]

demog_features = [
    { "name": "Age", "col": "age", "unit": "yr" }, 
    { "name": "Gender", "fn": lambda df: "Female" if df["gender_female"] == 1 else "Male" }, 
    "BMI",
    {
        "name": "Relevant Comorbidities",
        "list_positive": {
            "aids": "AIDS", 
            "blood_loss_anemia": "Blood Loss Anemia", 
            "cardiac_arrhythmias": "Cardiac Arrhythmias",
            "chronic_pulmonary": "Chronic Pulmonary",
            "congestive_heart_failure": "Congestive Heart Failure",
            "deficiency_anemias": "Deficiency Anemias",
            "diabetes_complicated": "Diabetes (complicated)",
            "diabetes_uncomplicated": "Diabetes (uncomplicated)",
            "fluid_electrolyte": "Fluid or Electrolyte Disorder",
            "hypertension": "Hypertension",
            "liver_disease": "Liver Disease",
            "lymphoma": "Lymphoma",
            "metastatic_cancer": "Metastatic Cancer",
            "peripheral_vascular": "Peripheral Vascular Disorder",
            "pulmonary_circulation": "Pulmonary Circulation Disorder",
            "renal_failure": "Renal Failure",
            "solid_tumor": "Solid Tumor",
            "valvular_disease": "Valvular Disease",
        }
    }
]

def value_is_abnormal(patient_row, feature_col):
    if feature_col not in NORMAL_RANGES: return False
    normal_range = NORMAL_RANGES[feature_col]
    if "female" in normal_range:
        if patient_row['gender_female']:
            normal_range = normal_range['female']
        else:
            normal_range = normal_range['male']
    return (("min" in normal_range and patient_row[feature_col] < normal_range['min']) or
            ("max" in normal_range and patient_row[feature_col] < normal_range['max']))
    
def create_state_dict(spec, patient_row):
    state_dicts = []
    for item in spec:
        result = {}
        source_col = None
        if isinstance(item, dict):
            if "list_positive" in item:
                result["value"] = [v for c, v in item["list_positive"].items() if patient_row[c]]
                if len(result["value"]) == 0: result["value"] = "None"
            elif "children" in item:
                children = create_state_dict(item["children"], patient_row)
                if not children: continue
                result["children"] = children
            elif "fn" in item:
                result["value"] = item["fn"](patient_row)
            else:
                source_col = item.get("col", item["name"])
                result["value"] = patient_row[source_col]
            if "unit" in item:
                result["unit"] = item["unit"]
            result["name"] = item["name"]
            if "expanded" in item:
                result["expanded"] = item["expanded"]
        else:
            result["value"] = patient_row[item]
            result["name"] = item
            source_col = item
        try:
            v = float(result["value"])
            numerical_value = v
            if isinstance(result["value"], (bool, np.bool_)):
                result["value"] = "Yes" if v else "No"
            elif v == int(v) or abs(v) > 1000:
                result["value"] = str(int(v))
            else:
                result["value"] = "{:.3g}".format(v)
        except: 
            numerical_value = None
        if numerical_value is not None and f"{result['name']} Delta" in patient_row:
            delta = patient_row[f"{result['name']} Delta"]
            if abs(delta) > abs(numerical_value) * 0.05:
                result["delta"] = 1 if delta > 0 else -1
            else:
                result["delta"] = 0
        if numerical_value is not None:
            result["abnormal"] = value_is_abnormal(patient_row, source_col)
        if f"{result['name']} Present" in patient_row:
            result["present"] = patient_row[f"{result['name']} Present"]
            if isinstance(item, dict) and item.get("exclude_missing", False) and not result["present"]:
                continue
        if f"{result['name']} Ever" in patient_row and result["value"] in ("Yes", "No"):
            result["value"] = "Yes" if result["value"] == "Yes" else ("Previously" if patient_row[f"{result['name']} Ever"] else "No")
        if "value" not in result or isinstance(result["value"], (dict, list)) or not pd.isna(result["value"]):
            state_dicts.append(result)
            
    return state_dicts
