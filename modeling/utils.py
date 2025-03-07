import numpy as np

def fluid_long_names(treatment_index, last_treatment=None):
    if treatment_index == 0:
        if last_treatment in (1, 2):
            return "stop IV fluids"
        elif last_treatment == 3:
            return "stop diuretics"
        return "give neither IV fluid nor diuretics"
    if treatment_index in (1, 2):
        fluid_str = "100 mL to 1 L of IV fluid" if treatment_index == 1 else "more than 1 L of IV fluid"
        if last_treatment == 3:
            return "stop diuretics and give " + fluid_str
        return "give " + fluid_str
    if treatment_index == 3:
        if last_treatment in (1, 2):
            return "stop IV fluids and give diuretics"
        return "give diuretics"
    return "unknown"

def vasopressor_long_names(treatment_index, last_treatment=None):
    if treatment_index == 0:
        if last_treatment in (1, 2):
            return "wean all vasopressors"
        return "not give vasopressors"
    if treatment_index == 1:
        if last_treatment == 2:
            return "wean secondary vasopressors"
        return "give one vasopressor"
    if treatment_index == 2:
        if last_treatment == 1:
            return "add another vasopressor"
        return "give multiple vasopressors"
    return "unknown"

TREATMENT_INFO = (
    {
        "num_actions": 4, 
        "name": "Volume", 
        "inconsistent_label": "choose inconsistent IV fluid strategies", 
        "long_names": fluid_long_names,
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
        "long_names": vasopressor_long_names,
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

