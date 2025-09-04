import numpy as np
import itertools
from utils import TREATMENT_INFO, make_forward_neighbors

class PrescriptivePeerInformation:
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
        def make_probability_rep(actions, idx, last):
            num_actions = TREATMENT_INFO[idx]["num_actions"]
            inconsistent_msg = TREATMENT_INFO[idx]["inconsistent_label"]
            long_names = TREATMENT_INFO[idx]["long_names"]
            short_names = TREATMENT_INFO[idx]["short_names"]
            probs = np.bincount(actions, minlength=num_actions) / len(actions)
            result = {
                "probs": [
                    {"policy": short_names[i],
                    "prob": probs[i]}
                    for i in range(num_actions)
                ]
            }
            if probs.max() <= 0.6:
                return {
                    **result,
                    "consistent": False,
                    "choice": inconsistent_msg,
                }
            return {
                **result,
                "consistent": True,
                "choice": long_names(np.argmax(probs), last),
                "choice_idx": np.argmax(probs),
                "choice_prob": probs.max()
            }
        
        return {
            "prediction": [
                {"tx": "Volume",
                "pred": make_probability_rep(neighbor_treatments[0], 0, last_treatment[0] if last_treatment is not None else None)},
                {"tx": "Vasopressors",
                "pred": make_probability_rep(neighbor_treatments[1], 1, last_treatment[1] if last_treatment is not None else None)},
            ],
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

class PrescriptiveOutcomeInformation:
    def __init__(self, train_neighbors, train_ids, train_outcome, train_treatments, severity_cutoffs=None, num_steps_forward=1):
        self.train_neighbors = train_neighbors
        self.train_ids = train_ids
        self.train_outcome = train_outcome
        self.num_steps_forward = num_steps_forward
        self.outcome_scores_train = np.zeros(len(train_outcome))
        for i, idx in enumerate(range(len(train_outcome))):
            self.outcome_scores_train[i] = train_outcome[train_neighbors[idx]].mean()
        self.train_treatments = train_treatments
        self.severity_cutoffs = severity_cutoffs

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
        # first get the indices of the next timestep in each nearest neighbor's trajectory
        neighbor_next_steps, neighbor_mask = make_forward_neighbors(neighbor_idxs.reshape(1, -1), 
                                                                    self.train_ids, 
                                                                    num_steps=self.num_steps_forward)
        neighbor_next_steps = neighbor_next_steps[0] # first row (only one instance)
        neighbor_mask = neighbor_mask[0]
        
        neighbor_treatments = tuple(np.take(self.train_treatments[:,i], neighbor_idxs)
                                for i in range(self.train_treatments.shape[1]))
        def mean_outcome(matching_idxs, next_idxs):
            if len(matching_idxs) / len(neighbor_idxs) < 0.1:
                return
            morta_scores = np.take(self.train_outcome, matching_idxs)
            return np.nanmean(morta_scores)
        
        all_predictions = {}
        for treatment_policy in itertools.product(*(range(info["num_actions"]) for info in TREATMENT_INFO)):
            treatment_mask = np.all(np.vstack([
                neighbor_treatments[i] == treatment_policy[i] for i in range(len(treatment_policy))
            ]), axis=0)
            idx_mask = np.logical_and(~neighbor_mask, treatment_mask)
            tx_outcome = mean_outcome(neighbor_idxs[idx_mask],
                                      neighbor_next_steps[idx_mask])
            if tx_outcome:
                all_predictions[treatment_policy] = (tx_outcome, idx_mask.sum())
        
        if not all_predictions:
            return None
        
        best_policy = sorted(all_predictions, key=all_predictions.get)[0]
        
        return {
            "recommendation": [{
                "tx": info["name"], 
                "value": info["short_names"][v], 
                "description": info["long_names"](v, last)
            } for info, v, last in zip(TREATMENT_INFO, best_policy, last_treatment if last_treatment is not None else [None] * len(best_policy))],
            "sample_size": all_predictions[best_policy][1],
            **({"ground_truth": [
                {"tx": info["name"], "label": info["short_names"][v]}
                for info, v in zip(TREATMENT_INFO, true_treatment)
            ]} if true_treatment is not None else {}),
            **({"severity_range": {
                "min": int(self.severity_cutoffs[severity_quantile]),
                "max": int(self.severity_cutoffs[severity_quantile + 1]),
            }} if self.severity_cutoffs is not None and severity_quantile is not None else {})
        }