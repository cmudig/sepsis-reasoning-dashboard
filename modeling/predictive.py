import numpy as np
from utils import make_forward_neighbors, TREATMENT_INFO
import scipy
from statsmodels.stats.proportion import proportions_ztest
import itertools

class PredictiveActionIndependentInformation:
    """
    Generates information about the likelihood of an outcome based on the nearest
    neighbors.
    """
    def __init__(self, train_outcome, train_severity_quantiles, severity_cutoffs):
        self.train_outcome = train_outcome
        self.train_severity_quantiles = train_severity_quantiles
        self.severity_cutoffs = severity_cutoffs
    
    def get_prediction(self, indexes, severity_quantile=None, true_outcome=None):
        """
        :param indexes: Indexes of the nearest neighbors to the point of interest
            in the training set.
        :param severity_quantile: Severity quantile integer for the point of
            interest.
        :param true_outcome: Boolean value indicating the true outcome for this
            instance; if provided, add the ground truth to the returned output.
        """
        pred = self.train_outcome[indexes].mean()
        base_rate = self.train_outcome[self.train_severity_quantiles == severity_quantile].mean()
        # IPCC guidelines
        # >99%	Virtually certain
        # >90%	Very likely
        # >66%	Likely
        # 33 to 66%	About as likely as not
        # <33%	Unlikely
        # <10%	Very unlikely
        # <1%	Exceptionally unlikely

        if pred <= 0.01:
            pred_str = "exceptionally unlikely"
        elif pred <= 0.1:
            pred_str = "very unlikely"
        elif pred <= 0.33:
            pred_str = "unlikely"
        elif pred <= 0.66:
            pred_str = "about as likely as not"
        elif pred <= 0.9:
            pred_str = "likely"
        elif pred <= 0.99:
            pred_str = "very likely"
        else:
            pred_str = "virtually certain"
            
        if pred / base_rate >= 2:
            base_rate_comp = {"base_rate_comparison": "much more likely"}
        elif pred > base_rate * 1.1:
            base_rate_comp = {"base_rate_comparison": "more likely"}
        elif pred < base_rate * 0.5:
            base_rate_comp = {"base_rate_comparison": "much less likely"}
        elif pred < base_rate * 0.9:
            base_rate_comp = {"base_rate_comparison": "less likely"}
        else:
            base_rate_comp = {"base_rate_comparison": "about as likely"}
    
        return {
            "prediction": pred_str,
            **({"ground_truth": "Yes" if true_outcome else "No"} if true_outcome is not None else {}),
            **base_rate_comp,
            "prediction_percentage": int(round(pred * 100)),
            "base_rate_percentage": int(round(base_rate * 100)),
            **({"severity_range": {
                "min": int(self.severity_cutoffs[severity_quantile]),
                "max": int(self.severity_cutoffs[severity_quantile + 1])
            }} if severity_quantile is not None else {}),
        }
        
class PredictiveActionDependentInformation:
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

    def get_prediction(self, neighbor_idxs, severity_quantile=None, true_outcome=None):
        # first get the indices of the next timestep in each nearest neighbor's trajectory
        neighbor_next_steps, neighbor_mask = make_forward_neighbors(neighbor_idxs.reshape(1, -1), 
                                                                    self.train_ids, 
                                                                    num_steps=self.num_steps_forward)
        neighbor_next_steps = neighbor_next_steps[0] # first row (only one instance)
        neighbor_mask = neighbor_mask[0]

        neighbor_treatments = tuple(np.take(self.train_treatments[:,i], neighbor_idxs)
                                for i in range(self.train_treatments.shape[1]))
        def make_outcome_rep(policy, matching_idxs, next_idxs, baseline_idxs=None, baseline_next_idxs=None):
            result = {"policy": [
                {"tx": TREATMENT_INFO[i]["name"], "value": TREATMENT_INFO[i]["short_names"][policy[i]]}
                for i in range(len(policy))
            ]} if policy is not None else {}
            if len(matching_idxs) / len(neighbor_idxs) < 0.1:
                return
            result["sample_size"] = len(matching_idxs)
            outcome_scores = np.take(self.train_outcome, matching_idxs)
            # outcome_scores = np.take(self.outcome_scores_train, next_idxs) - np.take(self.outcome_scores_train, matching_idxs)
            if baseline_idxs is not None:
                outcome_scores_base = np.take(self.train_outcome, baseline_idxs) # np.take(self.outcome_scores_train, baseline_next_idxs) - np.take(self.outcome_scores_train, baseline_idxs)
                outcome_t = proportions_ztest(np.array([outcome_scores.sum(), outcome_scores_base.sum()]),
                                              np.array([len(outcome_scores), len(outcome_scores_base)]))[1] # scipy.stats.ttest_ind(outcome_scores, outcome_scores_base)
            else:
                outcome_t = None
            result["prediction"] = {
                "mean": np.nanmean(outcome_scores),
                "std": np.nanstd(outcome_scores),
                **({"pvalue": outcome_t} if outcome_t is not None else {})
            }
            return result
        
        all_predictions = []
        for treatment_policy in itertools.product(*(range(tx['num_actions']) for tx in TREATMENT_INFO)):
            treatment_mask = np.all(np.vstack([
                neighbor_treatments[i] == treatment_policy[i] for i in range(len(treatment_policy))
            ]), axis=0)
            all_predictions.append(make_outcome_rep(treatment_policy,
                                                    neighbor_idxs[np.logical_and(~neighbor_mask, 
                                                                                treatment_mask)],
                                                    neighbor_next_steps[np.logical_and(~neighbor_mask, 
                                                                                    treatment_mask)],
                                                    neighbor_idxs[~neighbor_mask],
                                                    neighbor_next_steps[~neighbor_mask]))
        return {
            "predictions": [p for p in all_predictions if p],
            "average": make_outcome_rep(None, neighbor_idxs[~neighbor_mask], neighbor_next_steps[~neighbor_mask]),
            **({"ground_truth": "Yes" if true_outcome else "No"} if true_outcome is not None else {}),
            **({"severity_range": {
                "min": int(self.severity_cutoffs[severity_quantile]),
                "max": int(self.severity_cutoffs[severity_quantile + 1]),
            }} if severity_quantile is not None and self.severity_cutoffs is not None else {})
        }

