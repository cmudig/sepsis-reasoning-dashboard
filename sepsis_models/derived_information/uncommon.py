from sepsis_models.derived_information.utils import TREATMENT_INFO, fluid_long_names, vasopressor_long_names
import numpy as np

UNCOMMON_ACTION_CHOICES = [
    {
        "name": "No Fluids, Vasopressors, or Diuretics",
        "treatment_indexes": [[0], [0]],
        "excludes": ["No Fluids"],
        "long_name": lambda last: "give nothing"
    },
    # {
    #     "name": "Diuretics and Vasopressors",
    #     "treatment_indexes": [[3], [1, 2]],
    #     "excludes": ["Diuretics", "Vasopressors"],
    #     "long_name": lambda last: "give both diuretics and vasopressors"
    # },
    {
        "name": "No Fluids",
        "treatment_indexes": [[0], None],
        "long_name": lambda last: fluid_long_names(0, last[0])
    },
    {
        "name": "Fluids",
        "treatment_indexes": [[1], None],
        "excludes": ["< 1 L Fluids", ">= 1 L Fluids"],
        "long_name": lambda last: f"give fluids"
    },
    {
        "name": "Diuretics",
        "treatment_indexes": [[3], None],
        "long_name": lambda last: fluid_long_names(3, last[0])
    },
    {
        "name": "< 1 L Fluids",
        "treatment_indexes": [[1], None],
        "excludes": ["Fluids and Vasopressors"],
        "long_name": lambda last: fluid_long_names(1, last[0])
    },
    {
        "name": ">= 1 L Fluids",
        "treatment_indexes": [[2], None],
        "excludes": ["Fluids and Vasopressors"],
        "long_name": lambda last: fluid_long_names(2, last[0])
    },
    {
        "name": "Vasopressors",
        "treatment_indexes": [None, [1, 2]],
        "excludes": ["One Vasopressor", "Multiple Vasopressors", "Fluids and Vasopressors"],
        "long_name": lambda last: "give vasopressors"
    },
    {
        "name": "One Vasopressor",
        "treatment_indexes": [None, [1]],
        "excludes": ["Fluids and Vasopressors"],
        "long_name": lambda last: vasopressor_long_names(1, last[1])
    },
    {
        "name": "Multiple Vasopressors",
        "treatment_indexes": [None, [2]],
        "excludes": ["Fluids and Vasopressors"],
        "long_name": lambda last: vasopressor_long_names(2, last[1])
    },
    {
        "name": "Fluids and Vasopressors",
        "treatment_indexes": [[1, 2], [1, 2]],
        "long_name": lambda last: "give both fluids and vasopressors"
    },

]

MAX_UNCOMMON_COUNT = 20

class UncommonActionsInformation:
    def __init__(self, train_treatments, severity_cutoffs=None, min_consistent_probability=0.6):
        self.train_treatments = train_treatments
        self.severity_cutoffs = severity_cutoffs
        self.min_consistent_probability = min_consistent_probability
        
    def get_recommendation(self, neighbor_idxs, severity_quantile=None, true_treatment=None, last_treatment=None):
        """
        :param neighbor_idxs: Indexes of the nearest neighbors to the point of interest
            in the training set.
        :param severity_quantile: Severity quantile integer for the point of
            interest.
        :param true_treatment: Boolean value indicating the true treatment given 
            for this instance; if provided, add the ground truth to the returned 
            output.
        """
        neighbor_treatments = tuple(np.take(self.train_treatments[:,i], neighbor_idxs)
                        for i in range(self.train_treatments.shape[1]))
        actions = []
        exclude_actions = set()
        for action in UNCOMMON_ACTION_CHOICES:
            if action["name"] in exclude_actions: continue
            
            treatment_indexes = action["treatment_indexes"]
            matching_neighbor_idxs = None
            for k, tx_idxs in enumerate(treatment_indexes):
                if tx_idxs is None: continue
                if matching_neighbor_idxs is None:
                    matching_neighbor_idxs = np.isin(neighbor_treatments[k], tx_idxs)
                else:
                    matching_neighbor_idxs &= np.isin(neighbor_treatments[k], tx_idxs)
                    
            assert matching_neighbor_idxs is not None
            if matching_neighbor_idxs.sum() > 0 and matching_neighbor_idxs.sum() < MAX_UNCOMMON_COUNT:
                actions.append({
                    "short_name": action["name"],
                    "long_name": action["long_name"](last_treatment if last_treatment is not None else [None, None]),
                    "treatment_indexes": treatment_indexes,
                    "count": matching_neighbor_idxs.sum(),
                    "prob": matching_neighbor_idxs.mean()
                })
                exclude_actions |= set(action.get("excludes", []))
                
        return {
            "uncommon_actions": actions,
            **({"ground_truth": [
                {"tx": "Volume",
                "label": TREATMENT_INFO[0]["short_names"][true_treatment[0]],
                "label_idx": true_treatment[0]},
                {"tx": "Vasopressors",
                "label": TREATMENT_INFO[1]["short_names"][true_treatment[1]],
                "label_idx": true_treatment[1]},
            ]} if true_treatment is not None else {}),
            **({"severity_range": {
                "min": int(self.severity_cutoffs[severity_quantile]),
                "max": int(self.severity_cutoffs[severity_quantile + 1]),
            }} if severity_quantile is not None and self.severity_cutoffs is not None else {})
        }