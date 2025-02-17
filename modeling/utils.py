import numpy as np
TREATMENT_INFO = (
    {
        "num_actions": 4, 
        "name": "Volume", 
        "inconsistent_label": "choose inconsistent IV fluid strategies", 
        "long_names": [
            "administer less than 100 mL of IV fluid",
            "administer 100 mL to 1 L of IV fluid",
            "administer more than 1 L of IV fluid",
            "administer diuretics"],
        "short_names": [
            "< 100 mL Fluids",
            "100 mL - 1 L Fluids",
            "> 1 L Fluids",
            "Diuretics"]
    },
    {
        "num_actions": 3, 
        "name": "Vasopressors", 
        "inconsistent_label": "choose inconsistent vasopressor strategies", 
        "long_names": [
            "not administer vasopressors",
            "administer one vasopressor",
            "administer multiple vasopressors"],
        "short_names": [
            "None",
            "One",
            "Multiple"
        ]
    }
)

def make_forward_neighbors(neighbors, ids, num_steps=1):
    # assume that the original training set is ordered by time
    neighbor_next_steps = neighbors + num_steps
    neighbor_mask = np.zeros(neighbor_next_steps.shape, dtype=bool)
    # remove out-of-range indices first
    neighbor_mask |= neighbor_next_steps >= len(ids)
    neighbor_next_steps[neighbor_mask] = 0
    # remove timesteps that moved us to a different trajectory
    neighbor_mask |= np.take(ids.values, neighbor_next_steps) != np.take(ids.values, neighbors)
    neighbor_next_steps[neighbor_mask] = 0
    
    # represents the indexes of the next timesteps for each nearest neighbor,
    # for each training row, with missing or ended trajectories replaced with 0
    return neighbor_next_steps, neighbor_mask

