import numpy as np
import pandas as pd
import tqdm

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import torch.nn.functional as F

from sepsis_models.preprocessing.dataset import TemporalDataset
from .contrastive import TimeSeriesContrastiveLearner

from sepsis_models.models.utils import pad_collate, CausalConv1d, PositionalEncoding

device = 'cuda' if torch.cuda.is_available() else 'cpu'

class TripletContrastiveTrainer:
    def __init__(self, train_data, val_data, test_data,
                 train_treatments, val_treatments, test_treatments,
                 id_col="id", time_col="time",
                 architecture='transformer', nhead=4, nhid=128, nembed=32, 
                 nencoder=2, dropout=0.1, device='cpu', lr=5e-4,
                 triplet_margin=1.0,
                 lr_decay=0.98, n_warmup=2, corruption_rate=0.2, mask_prob=0.0,
                 num_triplets=128,
                 neg_same_traj_prob=0.5,
                 checkpoint_path=None):
        ninp = train_data.shape[1] - 2
        self.sequence_length = train_data[time_col].groupby(train_data[id_col]).count().max()
        self.corruption_rate = corruption_rate
        self.train_dataset = self.make_dataset(train_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                               treatments=train_treatments.values)
        self.val_dataset = self.make_dataset(val_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                               treatments=val_treatments.values)
        self.test_dataset = self.make_dataset(test_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                               treatments=test_treatments.values)
        
        self.device = device
        self.model = TimeSeriesContrastiveLearner(architecture=architecture, 
                                           ninp=ninp, 
                                           nhead=nhead, 
                                           nhid=nhid, 
                                           nembed=nembed, 
                                           nencoder=nencoder,
                                           dropout=dropout, 
                                           device=self.device).to(self.device)

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=0.1)
        scheduler1 = torch.optim.lr_scheduler.LinearLR(self.optimizer, total_iters=n_warmup)
        scheduler2 = torch.optim.lr_scheduler.StepLR(self.optimizer, 1, gamma=lr_decay)
        self.scheduler = torch.optim.lr_scheduler.SequentialLR(self.optimizer, schedulers=[scheduler1, scheduler2], milestones=[n_warmup])

        self.criterion = nn.TripletMarginLoss(margin=triplet_margin)
        self.checkpoint_path = checkpoint_path
        
        self.mask_prob = mask_prob
        self.neg_same_traj_prob = neg_same_traj_prob
        self.num_triplets = num_triplets
        
    def load_checkpoint(self):
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])
        
    def flatten_by_trajectories(self, items, lengths):
        return torch.cat(
            [x[:l] for x, l in zip(items, lengths)],
            0
        )

    def corrupt_input(self, inputs, lengths):
        """
        Perform SCARF corruption on the given inputs.
        """
        # inputs: (N, L, O), lengths: (N,)
        if self.corruption_rate == 0.0: return inputs
        
        N, L, O = inputs.shape
        corrupted = inputs.clone()
        all_possible_idxs = torch.cartesian_prod(torch.arange(N), torch.arange(L)).to(self.device)
        all_possible_idxs = all_possible_idxs[all_possible_idxs[:,1] < lengths[all_possible_idxs[:,0]]]
        for observation_dim in range(O):
            idxs_to_randomize = np.random.choice(all_possible_idxs.shape[0], size=int(self.corruption_rate * all_possible_idxs.shape[0]))
            idxs_to_swap = np.random.choice(all_possible_idxs.shape[0], size=int(self.corruption_rate * all_possible_idxs.shape[0]))
            corrupted[all_possible_idxs[idxs_to_randomize, 0], all_possible_idxs[idxs_to_randomize, 1], observation_dim] = inputs[all_possible_idxs[idxs_to_swap, 0], all_possible_idxs[idxs_to_swap, 1], observation_dim]
            
        if self.mask_prob > 0.0:
            should_mask = torch.rand(corrupted.shape).to(self.device) < self.mask_prob
            corrupted = torch.where(should_mask, 0.0, corrupted)
        return corrupted
    
    def make_triplets(self, embeddings, treatments, trajectory_indexes, timestep_numbers):
        """
        embeddings: (N, E)
        treatments: (N,)
        trajectory_indexes: (N,)
        Returns: anchors, positives, negatives (all (num_triplets, E))
        """
        N = embeddings.shape[0]
        anchors = []
        positives = []
        negatives = []
        idxs = np.arange(N)
        sampled_idxs = np.random.choice(N, size=min(self.num_triplets, N), replace=False)
        for anchor_idx in sampled_idxs:
            anchor_traj = trajectory_indexes[anchor_idx]
            anchor_treat = treatments[anchor_idx]

            # Positive: same treatment, different trajectory
            pos_mask = (treatments == anchor_treat) & (trajectory_indexes != anchor_traj)
            pos_candidates = idxs[pos_mask]
            if len(pos_candidates) == 0:
                continue  # skip if no positive found
            pos_idx = np.random.choice(pos_candidates)

            # Negative selection
            if np.random.rand() < self.neg_same_traj_prob:
                # Negative: same trajectory, different treatment
                neg_mask = (trajectory_indexes == anchor_traj) & (treatments != anchor_treat)
                neg_candidates = idxs[neg_mask]
                if len(neg_candidates) == 0:
                    # fallback to different trajectory and different treatment
                    neg_mask = (trajectory_indexes != anchor_traj) & (treatments != anchor_treat)
                    neg_candidates = idxs[neg_mask]
            else:
                # Negative: different trajectory, different treatment
                neg_candidates = []
                if anchor_idx >= 1 and timestep_numbers[anchor_idx] >= 1:
                    # find other indexes that have the same previous treatment but different future treatments
                    past_treatment = treatments[anchor_idx - 1]
                    neg_mask = ((trajectory_indexes != anchor_traj) & 
                                (timestep_numbers >= 1) & 
                                np.concatenate([np.array([False]), treatments[:-1] == past_treatment]) & 
                                (treatments != anchor_treat))
                    neg_candidates = idxs[neg_mask]
                if len(neg_candidates) == 0:
                    neg_mask = (trajectory_indexes != anchor_traj) & (treatments != anchor_treat)
                    neg_candidates = idxs[neg_mask]
                    if len(neg_candidates) == 0:
                        # fallback to same trajectory, different treatment
                        neg_mask = (trajectory_indexes == anchor_traj) & (treatments != anchor_treat)
                        neg_candidates = idxs[neg_mask]
            if len(neg_candidates) == 0:
                continue  # skip if no negative found
            neg_idx = np.random.choice(neg_candidates)

            anchors.append(embeddings[anchor_idx])
            positives.append(embeddings[pos_idx])
            negatives.append(embeddings[neg_idx])

        if len(anchors) == 0:
            raise ValueError("No valid triplets could be formed with the given data.")

        anchors = torch.stack(anchors)
        positives = torch.stack(positives)
        negatives = torch.stack(negatives)
        return anchors, positives, negatives
    
    def compute_loss(self, traj_embeddings, treatments, traj_lengths):
        traj_idxs = self.flatten_by_trajectories(torch.tile(torch.arange(traj_lengths.shape[0]).reshape(-1, 1), (1, traj_lengths.max())), traj_lengths).to(self.device)
        seq_idxs = self.flatten_by_trajectories(torch.tile(torch.arange(traj_lengths.max()), (traj_lengths.shape[0], 1)), traj_lengths).to(self.device)
        embeddings = self.flatten_by_trajectories(traj_embeddings, traj_lengths)
        treatments = self.flatten_by_trajectories(treatments, traj_lengths)
        anchors, positives, negatives = self.make_triplets(embeddings, treatments, traj_idxs, seq_idxs)
        return self.criterion(anchors, positives, negatives)
    
    def fit(self, epochs=20, batch_size=32, patience=10, loss_callback=None):        
        train_loader = DataLoader(self.train_dataset, batch_size=batch_size, shuffle=True, collate_fn=pad_collate)
        val_loader = DataLoader(self.val_dataset, batch_size=batch_size, collate_fn=pad_collate)
        num_without_improvement = 0
        best_loss = 1e9
        use_amp = self.model.model_type == 'transformer' and self.device == 'cuda'
        scaler = GradScaler(enabled=use_amp)
        for epoch in range(int(np.ceil(epochs))):
            print(f"Epoch {epoch}")
            bar = tqdm.tqdm(train_loader)
            # bar = train_loader
            total_loss = 0.0
            total_batches = 0
            self.model.train()
            for batch_idx, (inputs, _, weights, treatments, lengths) in enumerate(bar):
                if epoch + batch_idx / len(train_loader) >= epochs: break
                self.optimizer.zero_grad()
                with torch.autocast(device_type=self.device, dtype=torch.bfloat16 if self.device == 'cpu' else torch.float16, enabled=use_amp):
                    inputs = inputs.to(self.device)
                    lengths = lengths.to(self.device)
                    treatments = treatments.to(self.device)
                    corrupted = self.corrupt_input(inputs, lengths)
                    loss = self.compute_loss(self.model(corrupted), 
                                             treatments,
                                             lengths)
                scaler.scale(loss).backward()
                # torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
                scaler.step(self.optimizer)
                scaler.update()
                total_loss += loss.item()
                total_batches += 1
                bar.set_description(f"{total_loss / total_batches:.6f}")
            train_loss = total_loss / total_batches
            self.scheduler.step()
                
            self.model.eval()
            with torch.no_grad():
                bar = tqdm.tqdm(val_loader)
                # bar = val_loader
                total_loss = 0
                total_batches = 0
                for inputs, _, weights, treatments, lengths in bar:
                    with torch.autocast(device_type=self.device, dtype=torch.bfloat16 if self.device == 'cpu' else torch.float16, enabled=use_amp):
                        inputs = inputs.to(self.device)
                        lengths = lengths.to(self.device)
                        treatments = treatments.to(self.device)
                        corrupted = self.corrupt_input(inputs, lengths)
                        total_loss += self.compute_loss(self.model(corrupted), 
                                             treatments,
                                             lengths).item()
                        total_batches += 1

                        bar.set_description(f"Loss: {total_loss / total_batches:.6f}")
                    
            total_loss = total_loss / total_batches
            if loss_callback is not None:
                loss_callback(train_loss, total_loss)
            if total_loss <= best_loss:
                print("New best:", total_loss)
                num_without_improvement = 0
                best_loss = total_loss
                if self.checkpoint_path is not None:
                    self.save(self.checkpoint_path)
            else:
                num_without_improvement += 1
                if num_without_improvement == patience:
                    print("Early stop")
                    break
        return best_loss
    
    def save(self, checkpoint_path):
        torch.save({
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'scheduler': self.scheduler.state_dict()
        }, checkpoint_path)
    
    def make_dataset(self, df, id_col='id', time_col='time', **kwargs):
        return TemporalDataset(df[id_col].values,
                               df.drop(columns=[id_col, time_col]).values,
                               None,
                               **kwargs)

    def encode(self, dataset, batch_size=32):
        self.model.eval()
        loader = DataLoader(dataset, batch_size=batch_size, collate_fn=pad_collate)
        with torch.no_grad():
            bar = tqdm.tqdm(loader)
            all_predictions = []
            for inputs, outputs, weights, treatments, lengths in bar:
                inputs = inputs.to(self.device)
                lengths = lengths.to(self.device)
                preds = self.model(inputs)
                all_predictions.append(self.flatten_by_trajectories(preds, lengths).cpu().numpy())
        all_predictions = np.concatenate(all_predictions)
        return all_predictions
