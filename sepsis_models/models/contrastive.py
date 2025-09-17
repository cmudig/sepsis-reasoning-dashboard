import numpy as np
import pandas as pd
import tqdm

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import torch.nn.functional as F

from sepsis_models.preprocessing.dataset import TemporalDataset

from sepsis_models.models.utils import pad_collate, CausalConv1d, PositionalEncoding

device = 'cuda' if torch.cuda.is_available() else 'cpu'

class TimeSeriesContrastiveLearner(nn.Module):
    def __init__(self, architecture, ninp, nhead, nhid, nembed, nencoder, dropout=0.5, device='cpu'):
        super().__init__()
        self.ninp = ninp
        self.nencoder = nencoder
        self.nhid = nhid
        self.nembed = nembed
        self.model_type = architecture
        self.input_emb = nn.Linear(ninp, nhid)
        if self.model_type == 'transformer':
            self.pos_encoder = PositionalEncoding(nhid, dropout)
            self.layer_norm = nn.LayerNorm(nhid)
            encoder_layer = nn.TransformerEncoderLayer(d_model=nhid, nhead=nhead, dim_feedforward=nhid*4, dropout=dropout, batch_first=True)
            self.transformer = nn.TransformerEncoder(encoder_layer, nencoder)
        elif self.model_type == 'cnn':
            self.cnn_layers = [
                CausalConv1d(nhid, nhid, nhead)
                for _ in range(nencoder)
            ]
            self.batch_norm = [
                nn.BatchNorm1d(nhid)
                for _ in range(nencoder)
            ]
        elif self.model_type == 'rnn':
            self.rnn = nn.LSTM(nhid, nhid, num_layers=nencoder, batch_first=True, dropout=dropout)
        elif self.model_type == 'dense':
            self.dense = nn.ModuleList([
                nn.Linear(nhid, nhid) for _ in range(nencoder)
            ])
        self.encoder_dropout = nn.Dropout(dropout)
        self.bottleneck = nn.Linear(nhid, nembed)
        self.device = device

    def forward(self, src):
        src = self.input_emb(src) * np.sqrt(self.ninp)
        if self.model_type == 'transformer':
            src = self.layer_norm(self.pos_encoder(src))
            output = self.transformer(src, is_causal=True, mask=nn.Transformer.generate_square_subsequent_mask(src.shape[1]).to(self.device))
        elif self.model_type == 'rnn': 
            h0 = torch.randn(self.nencoder, src.shape[0], self.nhid).to(self.device)
            c0 = torch.randn(self.nencoder, src.shape[0], self.nhid).to(self.device)
            output, (hn, cn) = self.rnn(src, (h0, c0))
        elif self.model_type == 'cnn':
            output = src.permute(0, 2, 1)
            for layer, norm in zip(self.cnn_layers, self.batch_norm):
                output = norm(F.relu(layer(self.encoder_dropout(output))))
            output = output.permute(0, 2, 1)
        else:
            output = src
            for i, layer in enumerate(self.dense):
                output = layer(self.encoder_dropout(output))
                if i < len(self.dense) - 1: output = F.relu(output)
        return output    
    
def infonce_loss(temperature=0.07):
    """
    Computes the InfoNCE loss for a batch of embeddings.
    Args:
        z_i: Tensor of shape (batch_size, embed_dim) - anchor embeddings
        z_j: Tensor of shape (batch_size, embed_dim) - positive embeddings
        temperature: Scaling factor for logits
    Returns:
        Scalar InfoNCE loss
    """
    def loss_fn(z_i, z_j, labels, mask=None):
        """
        Args:
            z_i: (N, D) anchor embeddings
            z_j: (M, D) positive/negative embeddings
            labels: (N, M) binary matrix, 1 for positive, 0 for negative
            mask: (N, M) binary matrix, 1 to keep, 0 to mask out (optional)
        Returns:
            Scalar InfoNCE loss
        """
        z_i = F.normalize(z_i, dim=1)
        z_j = F.normalize(z_j, dim=1)
        if mask is not None: mask = mask > 0
        logits = torch.matmul(z_i, z_j.T) / temperature  # (N, M)

        if mask is not None:
            logits = logits * mask + ~mask * (-1e9)

        # For each anchor, compute log-softmax over all z_j
        log_probs = F.softmax(logits, dim=1)  # (N, M)

        # Only sum over positive pairs as indicated by labels
        loss = - torch.log((labels * log_probs).sum(1)).sum() / (labels.sum() + 1e-8)
        return loss
    return loss_fn
    
class TimeSeriesContrastiveTrainer:
    def __init__(self, train_data, val_data, test_data,
                 id_col="id", time_col="time",
                 architecture='transformer', nhead=4, nhid=128, nembed=32, 
                 nencoder=2, dropout=0.1, device='cpu', lr=5e-4,
                 lr_decay=0.98, n_warmup=2, corruption_rate=0.2,
                 infonce_temperature=0.07,
                 checkpoint_path=None,
                 same_trajectory_contrast_lambda=0.0,
                 other_trajectory_contrast_lambda=0.0,
                train_weights=None, val_weights=None, test_weights=None):
        ninp = train_data.shape[1] - 2
        self.sequence_length = train_data[time_col].groupby(train_data[id_col]).count().max()
        self.corruption_rate = corruption_rate
        self.train_dataset = self.make_dataset(train_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                             weights=train_weights)
        self.val_dataset = self.make_dataset(val_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                             weights=val_weights)
        self.test_dataset = self.make_dataset(test_data,
                                               id_col=id_col,
                                               time_col=time_col,
                                             weights=test_weights)
        self.device = device
        self.model = TimeSeriesContrastiveLearner(architecture=architecture, 
                                           ninp=ninp, 
                                           nhead=nhead, 
                                           nhid=nhid, 
                                           nembed=nembed, 
                                           nencoder=nencoder,
                                           dropout=dropout, 
                                           device=self.device).to(self.device)
        self.same_trajectory_contrast_lambda = same_trajectory_contrast_lambda
        self.other_trajectory_contrast_lambda = other_trajectory_contrast_lambda

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=0.1)
        scheduler1 = torch.optim.lr_scheduler.LinearLR(self.optimizer, total_iters=n_warmup)
        scheduler2 = torch.optim.lr_scheduler.StepLR(self.optimizer, 1, gamma=lr_decay)
        self.scheduler = torch.optim.lr_scheduler.SequentialLR(self.optimizer, schedulers=[scheduler1, scheduler2], milestones=[n_warmup])

        self.criterion = infonce_loss(temperature=infonce_temperature)
        self.checkpoint_path = checkpoint_path
        
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
        return corrupted
    
    def same_trajectory_loss(self, flat_preds, flat_corrupted_preds, lengths):
        traj_idxs = self.flatten_by_trajectories(torch.tile(torch.arange(lengths.shape[0]).reshape(-1, 1), (1, lengths.max())), lengths)
        seq_idxs = self.flatten_by_trajectories(torch.tile(torch.arange(lengths.max()), (lengths.shape[0], 1)), lengths)
        return self.criterion(flat_preds,
                              flat_corrupted_preds,
                              torch.abs(seq_idxs.reshape(-1, 1) - seq_idxs.reshape(1, -1)) <= 1,
                              mask=traj_idxs.reshape(-1, 1) == traj_idxs.reshape(1, -1))

    def other_trajectory_loss(self, flat_preds, flat_corrupted_preds, lengths):
        traj_idxs = self.flatten_by_trajectories(torch.tile(torch.arange(lengths.shape[0]).reshape(-1, 1), (1, lengths.max())), lengths)
        return self.criterion(flat_preds,
                              flat_corrupted_preds,
                              traj_idxs.reshape(-1, 1) == traj_idxs.reshape(1, -1))
        

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
            for batch_idx, (inputs, outputs, weights, lengths) in enumerate(bar):
                if epoch + batch_idx / len(train_loader) >= epochs: break
                self.optimizer.zero_grad()
                with torch.autocast(device_type=self.device, dtype=torch.bfloat16 if self.device == 'cpu' else torch.float16, enabled=use_amp):
                    inputs = inputs.to(self.device)
                    weights = weights.to(self.device)
                    lengths = lengths.to(self.device)
                    corrupted = self.corrupt_input(inputs, lengths)
                    preds = self.flatten_by_trajectories(self.model(inputs), lengths)
                    corrupted_preds = self.flatten_by_trajectories(self.model(corrupted), lengths)
                    
                    loss = self.criterion(preds, corrupted_preds, torch.eye(preds.shape[0]))
                    output_idx = 1
                    if self.same_trajectory_contrast_lambda > 0:
                        loss += (self.same_trajectory_contrast_lambda * 
                                 self.same_trajectory_loss(preds, corrupted_preds, lengths))
                        output_idx += 1
                    if self.other_trajectory_contrast_lambda > 0:
                        loss += (self.other_trajectory_contrast_lambda * 
                                 self.other_trajectory_loss(preds, corrupted_preds, lengths))
                        output_idx += 1
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
                total_losses = [0] * (1 + (1 if self.same_trajectory_contrast_lambda > 0 else 0) + (1 if self.other_trajectory_contrast_lambda > 0 else 0))
                total_batches = 0
                for inputs, outputs, weights, lengths in bar:
                    with torch.autocast(device_type=self.device, dtype=torch.bfloat16 if self.device == 'cpu' else torch.float16, enabled=use_amp):
                        inputs = inputs.to(self.device)
                        lengths = lengths.to(self.device)
                        weights = weights.to(self.device)
                        corrupted = self.corrupt_input(inputs, lengths)
                        preds = self.flatten_by_trajectories(self.model(inputs), lengths)
                        corrupted_preds = self.flatten_by_trajectories(self.model(corrupted), lengths)
                        
                        total_losses[0] += self.criterion(preds, corrupted_preds, torch.eye(preds.shape[0])).item()
                        output_idx = 1
                        if self.same_trajectory_contrast_lambda > 0:
                            total_losses[output_idx] += (self.same_trajectory_contrast_lambda * 
                                    self.same_trajectory_loss(preds, corrupted_preds, lengths))
                            output_idx += 1
                        if self.other_trajectory_contrast_lambda > 0:
                            total_losses[output_idx] += (self.other_trajectory_contrast_lambda * 
                                    self.other_trajectory_loss(preds, corrupted_preds, lengths))
                            output_idx += 1
                        total_batches += 1

                        loss_strings = [f"{l / total_batches:.6f}" for l in total_losses]
                        bar.set_description(f"Loss: {', '.join(loss_strings)}")
                    
            total_loss = sum(total_losses) / total_batches
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
            for inputs, outputs, weights, lengths in bar:
                inputs = inputs.to(self.device)
                lengths = lengths.to(self.device)
                preds = self.model(inputs)
                all_predictions.append(self.flatten_by_trajectories(preds, lengths).cpu().numpy())
        all_predictions = np.concatenate(all_predictions)
        return all_predictions
