import pandas as pd
import numpy as np
import tqdm
import faiss                   

def get_nearest_neighbors(test_encoded, reference_encoded, reference_ids, knearest=100, search_factor=2, neighbors=None, reference_identical=False, stratify=None, max_neighbors_to_search=1000):
    """
    Returns two matrices of shape (len(test_encoded), knearest), containing the indexes
    and distances respectively of the nearest neighbors by cosine similarity within the 
    reference encoded set.
    If stratify is not None, should be a tuple of two vectors of integers, the first with 
    the same length as test_encoded and the second with the same length as reference_encoded. 
    For each integer value, neighbors will be computed within all reference rows with the 
    same value.
    """
    if stratify is not None:
        test_strat, ref_strat = stratify
        result_dists = np.zeros((len(test_encoded), knearest), dtype=np.float32)
        result_idxs = np.zeros((len(test_encoded), knearest), dtype=int)
        for val in np.unique(test_strat):
            print(f"stratify value {val}")
            mask = test_strat == val
            ref_mask = ref_strat == val
            strat_idxs, strat_dists = get_nearest_neighbors(
                test_encoded[mask],
                reference_encoded[ref_mask],
                reference_ids[ref_mask],
                knearest=knearest,
                search_factor=search_factor,
                reference_identical=reference_identical,
                max_neighbors_to_search=max_neighbors_to_search
            )
            result_dists[mask] = strat_dists
            result_idxs[mask] = np.take(np.arange(len(reference_encoded))[ref_mask], strat_idxs) # convert the new indexes back to the full dataset
        return result_idxs, result_dists
    
    if neighbors is None:
        cell_index = faiss.IndexFlatIP(reference_encoded.shape[1])
        index = faiss.IndexIVFFlat(cell_index, reference_encoded.shape[1], min(reference_encoded.shape[0] // 100, 100))
        print("Training index")
        index.train(reference_encoded)
        print("Adding vectors to index")
        index.add(reference_encoded)
        index.nprobe = 10
        print(index.ntotal)
        neighbors = index # NearestNeighbors(n_neighbors=knearest * search_factor, metric='cosine')
        # neighbors.fit(reference_encoded)
    
    result_dists = np.zeros((len(test_encoded), knearest), dtype=np.float32)
    result_idxs = np.zeros((len(test_encoded), knearest), dtype=int)
    insufficient_neighbors = []
    
    for i in tqdm.tqdm(range(len(test_encoded))):
        # dists, idxs = neighbors.kneighbors(test_encoded[i:i + 1], n_neighbors=knearest * search_factor)
        dists, idxs = neighbors.search(test_encoded[i:i + 1], knearest * search_factor)
        dists = dists[0]
        idxs = idxs[0]
        ids = reference_ids[idxs]
        if reference_identical:
            # comparing the same arrays, so remove neighbors corresponding to the same trajectory
            same_id = ids == reference_ids[i]
            idxs = idxs[~same_id]
            dists = dists[~same_id]
            ids = ids[~same_id]
        unique_idxs = np.sort(np.unique(ids, return_index=True)[1])
        if len(unique_idxs) >= knearest:
            result_dists[i] = dists[unique_idxs[:knearest]]
            result_idxs[i] = idxs[unique_idxs[:knearest]]
        elif knearest * search_factor >= max_neighbors_to_search:
            neigh_idxs = unique_idxs[:max_neighbors_to_search]
            result_dists[i,:len(neigh_idxs)] = dists[neigh_idxs]
            result_idxs[i,:len(neigh_idxs)] = idxs[neigh_idxs]
            result_dists[i,len(neigh_idxs):] = np.nan
            result_idxs[i,len(neigh_idxs):] = -1
        else:
            insufficient_neighbors.append(i)
            
    if len(insufficient_neighbors) > 0:
        insufficient_neighbors = np.array(insufficient_neighbors)
        print(f"{len(insufficient_neighbors)} rows with insufficient neighbors")
        insuf_idxs, insuf_dists = get_nearest_neighbors(
            test_encoded[insufficient_neighbors],
            reference_encoded,
            reference_ids,
            knearest=knearest,
            search_factor=search_factor + 1,
            neighbors=neighbors,
            reference_identical=reference_identical,
            max_neighbors_to_search=max_neighbors_to_search
        )
        result_dists[insufficient_neighbors] = insuf_dists
        result_idxs[insufficient_neighbors] = insuf_idxs
        
    return result_idxs, result_dists