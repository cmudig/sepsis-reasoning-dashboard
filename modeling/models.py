import numpy as np
import pandas as pd
import tqdm

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import torch.nn.functional as F

from sklearn.preprocessing import StandardScaler

device = 'cuda' if torch.cuda.is_available() else 'cpu'

from torch.nn.utils.rnn import pad_sequence

def pad_collate(batch):
    """
    Helper function for DataLoader that takes an iterable of tuples containing
    variable-length tensors, and combines them together into a tuple of stacked
    tensors padded to the maximum length. Also adds a tensor to the end of the
    tuple containing the lengths of each sequence.
    """
    arrays_to_pad = list(zip(*batch))
    x_lens = [len(x) for x in arrays_to_pad[0]]

    padded_arrays = [pad_sequence(xx, batch_first=True, padding_value=0) for xx in arrays_to_pad]
    return (*padded_arrays, torch.LongTensor(x_lens))

class DataNormalization:
    """
    Handles all normalization of MIMIC and eICU state and demographics data.
    """
    
    def __init__(self, training_data, scaler=None, as_is_columns=[], norm_columns=[], log_norm_columns=[], clamp_magnitude=None):
        self.as_is_columns = as_is_columns
        self.norm_columns = norm_columns
        self.log_norm_columns = log_norm_columns
        self.clamp_magnitude = clamp_magnitude
        if scaler is not None:
            self.scaler = scaler
        else:
            self.scaler = StandardScaler()
            scores_to_norm = np.hstack([training_data[self.norm_columns].values.astype(np.float64),
                                        self._clip_and_log_transform(training_data[self.log_norm_columns].fillna(np.nan).values.astype(np.float64))])
            self.scaler.fit(scores_to_norm)

    def _preprocess_normalized_data(self, MIMICzs):
        """Performs ad-hoc normalization on the normalized variables."""
        
        # MIMICzs[pd.isna(MIMICzs)] = 0
        # MIMICzs[C_MAX_DOSE_VASO] = np.log(MIMICzs[C_MAX_DOSE_VASO] + 6)   # MAX DOSE NORAD 
        # MIMICzs[C_INPUT_STEP] = 2 * MIMICzs[C_INPUT_STEP]   # increase weight of this variable
        if self.clamp_magnitude is not None:
            MIMICzs = MIMICzs.where(np.abs(MIMICzs) < self.clamp_magnitude, pd.NA)
        return MIMICzs

    def _clip_and_log_transform(self, data, log_gamma=0.1):
        """Performs a log transform log(gamma + x), and clips x values less than zero to zero."""
        return np.log(log_gamma + np.clip(data, 0, None))
    
    def _inverse_log_transform(self, data, log_gamma=0.1):
        """Performs the inverse of the _clip_and_log_transform function (without the clipping)."""
        return np.exp(data) - log_gamma

    def transform(self, data):
        no_norm_scores = data[self.as_is_columns].astype(np.float64).values - 0.5
        scores_to_norm = np.hstack([data[self.norm_columns].values.astype(np.float64),
                                    self._clip_and_log_transform(data[self.log_norm_columns].fillna(np.nan).values.astype(np.float64))])
        normed = self.scaler.transform(scores_to_norm)
        
        MIMICzs = pd.DataFrame(np.hstack([no_norm_scores, normed]), columns=self.as_is_columns + self.norm_columns + self.log_norm_columns)
        return self._preprocess_normalized_data(MIMICzs)
    
    def inverse_transform(self, data):
        no_norm_scores = data[:,:len(self.as_is_columns)] + 0.5
        unnormed = self.scaler.inverse_transform(data[:,len(self.as_is_columns):])
        unnormed[:,len(self.norm_columns):] = self._inverse_log_transform(unnormed[:,len(self.norm_columns):])
        return pd.DataFrame(np.hstack([no_norm_scores, unnormed]), columns=self.as_is_columns + self.norm_columns + self.log_norm_columns)
        

class TemporalDataset(torch.utils.data.Dataset):
    """
    A dataset that creates sequence-level items containing inputs and outputs.
    """
    def __init__(self, 
                 stay_ids, 
                 observations, 
                 outputs,
                 mask_prob=0.0,
                 noise_factor=0.0,
                 replacement_values=0.0,
                 weights=None):
        """
        stay_ids, observations, and outputs should all be the same length.
        mask_prob = probability of zeroing any value when returned.
        noise_factor = factor for Gaussian noise to add to inputs
        weights = vector of same length as stay_ids containing numerical weights to apply to each timestep
        """
        assert len(stay_ids) == len(observations)
        self.observations = observations
        self.outputs = outputs
        self.stay_ids = stay_ids
        self.weights = weights
        
        self.stay_id_pos = []
        last_stay_id = None
        for i, stay_id in enumerate(self.stay_ids):
            if last_stay_id != stay_id:
                if self.stay_id_pos:
                    self.stay_id_pos[-1] = (self.stay_id_pos[-1][0], i)
                    assert i - 1 > self.stay_id_pos[-1][0], last_stay_id
                self.stay_id_pos.append((i, 0))
                last_stay_id = stay_id
        self.stay_id_pos[-1] = (self.stay_id_pos[-1][0], len(self.stay_ids))
        
        self.noise_factor = noise_factor
        self.mask_prob = mask_prob
        self.replacement_values = replacement_values
   
    def __len__(self):
        return len(self.stay_id_pos)
            
    def __getitem__(self, index):
        """
        Returns:
            observation sequence (N, L, S)
            outputs (N, L, 1)
            sequence lengths (N,)
        """
        trajectory_indexes = np.arange(*self.stay_id_pos[index])
        assert len(trajectory_indexes) > 0
        observations = self.observations[trajectory_indexes]
        if self.outputs is not None:
            outputs = self.outputs[trajectory_indexes]
        else:
            outputs = np.zeros(len(trajectory_indexes))
        if self.weights is not None:
            weights = self.weights[trajectory_indexes]
        else:
            weights = np.ones(len(trajectory_indexes))
        
        # Mask if needed
        input_obs = observations.copy()
        if self.noise_factor > 0.0:
            input_obs = input_obs + np.random.normal(size=input_obs.shape) * self.noise_factor
        if self.mask_prob > 0.0:
            # Randomly replace observation values with the median
            should_mask = np.random.uniform(0.0, 1.0, size=input_obs.shape) < self.mask_prob
            input_obs = np.where(should_mask, self.replacement_values, input_obs)
               
        return (
            torch.from_numpy(input_obs).float(), 
            torch.from_numpy(outputs).float(),
            torch.from_numpy(weights).float()
        )

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)
    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)
    
class CausalConv1d(nn.Conv1d):
    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size,
                 stride=1,
                 dilation=1,
                 groups=1,
                 bias=True):
        super(CausalConv1d, self).__init__(
            in_channels,
            out_channels,
            kernel_size,
            stride=stride,
            padding=0,
            dilation=dilation,
            groups=groups,
            bias=bias)

        self.left_padding = dilation * (kernel_size - 1)

    def forward(self, input):
        x = F.pad(input.unsqueeze(2), (self.left_padding, 0, 0, 0)).squeeze(2)

        return super(CausalConv1d, self).forward(x)
    
class TimeSeriesAutoencoder(nn.Module):
    def __init__(self, architecture, ninp, nhead, nhid, nembed, nencoder, ndecoder, dropout=0.5, device='cpu'):
        super().__init__()
        self.ninp = ninp
        self.nencoder = nencoder
        self.ndecoder = ndecoder
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
        self.decoder = nn.ModuleList([
            nn.Linear(nembed if i == 0 else nhid, nhid)
            for i in range(ndecoder)
        ])
        self.decoder_dropout = nn.Dropout(dropout)
        self.decoder2 = nn.Linear(nhid, ninp)
        self.device = device

    def encode(self, src):
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
            for layer in self.dense:
                output = F.relu(layer(self.encoder_dropout(output)))
        return self.bottleneck(self.encoder_dropout(output))
    
    def forward(self, src):
        # src = src.permute(1, 0, 2)
        output = self.encode(src)
        for layer in self.decoder:
            output = self.decoder_dropout(F.relu(layer(output)))
        output = self.decoder2(output)
        # output = output.permute(1, 0, 2)
        return output
    
class TimeSeriesAutoencoderTrainer:
    def __init__(self, train_data, val_data, test_data, id_col="id", time_col="time", architecture='transformer', nhead=4, nhid=128, nembed=64, nencoder=2, ndecoder=2, dropout=0.1, device='cpu', lr=5e-4, lr_decay=0.98, n_warmup=2, mask_gamma=1, change_lambda=0.0, shift_epochs=0, checkpoint_path=None, train_weights=None, val_weights=None, test_weights=None, output_exclude_cols=None):
        ninp = train_data.shape[1] - 2
        self.sequence_length = train_data[time_col].groupby(train_data[id_col]).count().max()
        self.output_exclude_mask = (torch.from_numpy(~train_data.drop(columns=[id_col, time_col]).columns.isin(output_exclude_cols)) 
                                    if output_exclude_cols else torch.ones(len(train_data.columns) - 2)).to(device)
        self.train_dataset = TemporalDataset(train_data[id_col].values,
                                             train_data.drop(columns=[id_col, time_col]).values,
                                             None,
                                             noise_factor=0.05,
                                             mask_prob=0.05,
                                             weights=train_weights)
        self.val_dataset = TemporalDataset(val_data[id_col].values,
                                             val_data.drop(columns=[id_col, time_col]).values,
                                             None,
                                             weights=val_weights)
        self.test_dataset = TemporalDataset(test_data[id_col].values,
                                             test_data.drop(columns=[id_col, time_col]).values,
                                             None,
                                             weights=test_weights)
        self.device = device
        self.model = TimeSeriesAutoencoder(architecture=architecture, ninp=ninp, nhead=nhead, nhid=nhid, nembed=nembed, nencoder=nencoder, ndecoder=ndecoder, dropout=dropout, device=self.device).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=0.1)
        scheduler1 = torch.optim.lr_scheduler.LinearLR(self.optimizer, total_iters=n_warmup)
        scheduler2 = torch.optim.lr_scheduler.StepLR(self.optimizer, 1, gamma=lr_decay)
        self.scheduler = torch.optim.lr_scheduler.SequentialLR(self.optimizer, schedulers=[scheduler1, scheduler2], milestones=[n_warmup])
        # self.scheduler = torch.optim.lr_scheduler.CyclicLR(self.optimizer, lr, 0.05, mode='triangular2', cycle_momentum=False, step_size_up=1000)
        self.criterion = nn.MSELoss(reduction='none')
        self.checkpoint_path = checkpoint_path
        self.mask_gamma = mask_gamma
        self.change_lambda = change_lambda
        self.shift_epochs = shift_epochs
        
    def load_checkpoint(self):
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])
        
    def fit(self, epochs=20, batch_size=32, patience=10, loss_callback=None):        
        train_loader = DataLoader(self.train_dataset, batch_size=batch_size, shuffle=True, collate_fn=pad_collate)
        val_loader = DataLoader(self.val_dataset, batch_size=batch_size, collate_fn=pad_collate)
        num_without_improvement = 0
        best_loss = 1e9
        weight_temperature = 1
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
                    preds = self.model(inputs)
                    if torch.isnan(preds).any():
                        print("Nan predictions", torch.isnan(inputs).sum(), lengths)
                    scaled_weights = torch.exp(weights / weight_temperature) / torch.sum(torch.where(weights > 0, torch.exp(weights / weight_temperature), 0.0))
                    if self.shift_epochs > 0:
                        shifted_inputs = torch.cat([inputs[:,1:,:], torch.zeros(inputs.shape[0], 1, inputs.shape[2]).to(self.device)], 1) - inputs
                        loss = self.change_lambda * (1 - 0.5 * ((preds / (torch.linalg.norm(preds, 2, 2, keepdim=True) + 1e-3)) * (shifted_inputs / (torch.linalg.norm(shifted_inputs, 2, 2, keepdim=True) + 1e-3))).sum(2))
                    else:
                        shifted_inputs = inputs
                        loss = 0
                    mse_loss = (self.criterion(preds, shifted_inputs) * (scaled_weights * (weights > 0).sum()).unsqueeze(-1))
                    mse_loss[:,:,~self.output_exclude_mask] = 0
                    loss += mse_loss.sum(2)
                    # loss += self.change_lambda * torch.linalg.norm(shifted_inputs - inputs, 2, 2)
                    loss_mask = torch.arange(loss.shape[1]).to(self.device)[None, :] < lengths[:, None] - self.shift_epochs
                    loss_masked = loss.where(loss_mask, torch.tensor(0.0).to(self.device))
                    loss = loss_masked.sum() / (loss_mask.sum() + 1e-3)
                scaler.scale(loss).backward()
                # torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
                scaler.step(self.optimizer)
                scaler.update()
                total_loss += loss.item()
                total_batches += 1
                bar.set_description(f"{total_loss / total_batches:.6f}")
            train_loss = total_loss / total_batches
            self.scheduler.step()
            self.train_dataset.mask_prob = min(self.train_dataset.mask_prob * self.mask_gamma, 0.6)
            self.train_dataset.noise_factor = min(self.train_dataset.noise_factor * self.mask_gamma, 1.0)
            weight_temperature *= 1.1
                
            self.model.eval()
            with torch.no_grad():
                bar = tqdm.tqdm(val_loader)
                # bar = val_loader
                total_loss = 0.0
                total_batches = 0
                total_mse = 0.0
                for inputs, outputs, weights, lengths in bar:
                    with torch.autocast(device_type=self.device, dtype=torch.bfloat16 if self.device == 'cpu' else torch.float16, enabled=use_amp):
                        inputs = inputs.to(self.device)
                        weights = weights.to(self.device)
                        lengths = lengths.to(self.device)
                        preds = self.model(inputs)
                        scaled_weights = torch.exp(weights / weight_temperature) / torch.sum(torch.where(weights > 0, torch.exp(weights / weight_temperature), 0.0))
                        if self.shift_epochs > 0:
                            shifted_inputs = torch.cat([inputs[:,1:,:], torch.zeros(inputs.shape[0], 1, inputs.shape[2]).to(self.device)], 1) - inputs
                            # loss = 1 - 0.5 * ((preds / torch.linalg.norm(preds, 2, keepdim=True)) * (shifted_inputs / torch.linalg.norm(shifted_inputs, 2, keepdim=True))).sum(2)
                        else:
                            shifted_inputs = inputs
                            # loss = (self.criterion(preds, shifted_inputs) * (scaled_weights * (weights > 0).sum()).unsqueeze(-1)).mean(2)
                        loss = (self.criterion(preds, shifted_inputs) * (scaled_weights * (weights > 0).sum()).unsqueeze(-1))
                        loss[:,:,~self.output_exclude_mask] = 0
                        loss = loss.mean(2)
                        # loss = (self.criterion(preds, shifted_inputs) * (scaled_weights * (weights > 0).sum()).unsqueeze(-1)).mean(2)
                        loss_mask = torch.arange(loss.shape[1]).to(self.device)[None, :] < lengths[:, None] - self.shift_epochs
                        loss_masked = loss.where(loss_mask, torch.tensor(0.0).to(self.device))
                        loss = loss_masked.sum() / loss_mask.sum()
                        total_loss += loss.item()
                        total_batches += 1

                        bar.set_description(f"Loss: {total_loss / total_batches:.6f}")
                    
            total_loss /= total_batches
            if loss_callback is not None:
                loss_callback(train_loss, total_loss)
            if total_loss <= best_loss:
                # print("New best:", total_loss)
                num_without_improvement = 0
                best_loss = total_loss
                if self.checkpoint_path is not None:
                    self.save(self.checkpoint_path)
            else:
                num_without_improvement += 1
                if num_without_improvement == patience:
                    # print("Early stop")
                    break
        return best_loss
    
    def save(self, checkpoint_path):
        torch.save({
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'scheduler': self.scheduler.state_dict()
        }, checkpoint_path)
    
    def encode(self, batch_size=32, split='test'):
        self.model.eval()
        loader = DataLoader({
            'train': self.train_dataset, 
            'val': self.val_dataset,
            'test': self.test_dataset
        }[split], batch_size=batch_size, collate_fn=pad_collate)
        with torch.no_grad():
            bar = tqdm.tqdm(loader)
            all_predictions = []
            for inputs, outputs, weights, lengths in bar:
                inputs = inputs.to(self.device)
                lengths = lengths.to(self.device)
                preds = self.model.encode(inputs)
                all_predictions.append(np.concatenate([x[:l].cpu().numpy() for x, l in zip(preds, lengths)]))
        all_predictions = np.concatenate(all_predictions)
        return all_predictions
