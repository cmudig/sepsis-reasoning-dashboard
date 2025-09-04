import numpy as np
import pandas as pd
import tqdm

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import torch.nn.functional as F

from sepsis_models.preprocessing.dataset import TemporalDataset

from sepsis_models.models.utils import CausalConv1d, PositionalEncoding

class TransformerClassifier(nn.Module):
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
        self.classifier = nn.Linear(nembed, 1)
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
            for layer in self.dense:
                output = F.relu(layer(self.encoder_dropout(output)))
        output = self.encoder_dropout(F.relu(self.bottleneck(self.encoder_dropout(output))))
        return self.classifier(output)
    
class TransformerClassifierTrainer:
    def __init__(self, train_data, val_data, test_data, train_labels, val_labels, test_labels, id_col="id", time_col="time", architecture='transformer', nhead=4, nhid=128, nembed=64, nencoder=2, ndecoder=2, dropout=0.1, device='cpu', lr=5e-4, lr_decay=0.98, n_warmup=2, mask_gamma=1, checkpoint_path=None, train_weights=None, val_weights=None, test_weights=None):
        ninp = train_data.shape[1] - 2
        self.sequence_length = train_data[time_col].groupby(train_data[id_col]).count().max()
        self.train_dataset = TemporalDataset(train_data[id_col].values,
                                             train_data.drop(columns=[id_col, time_col]).values,
                                             train_labels.values if isinstance(train_labels, pd.Series) else train_labels,
                                             noise_factor=0.05,
                                             mask_prob=0.05,
                                             weights=train_weights)
        self.val_dataset = TemporalDataset(val_data[id_col].values,
                                             val_data.drop(columns=[id_col, time_col]).values,
                                             val_labels.values if isinstance(val_labels, pd.Series) else val_labels,
                                             weights=val_weights)
        self.test_dataset = TemporalDataset(test_data[id_col].values,
                                             test_data.drop(columns=[id_col, time_col]).values,
                                             test_labels.values if isinstance(test_labels, pd.Series) else test_labels,
                                             weights=test_weights)
        self.device = device
        self.model = TransformerClassifier(architecture=architecture, ninp=ninp, nhead=nhead, nhid=nhid, nembed=nembed, nencoder=nencoder, ndecoder=ndecoder, dropout=dropout, device=self.device).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=0.1)
        scheduler1 = torch.optim.lr_scheduler.LinearLR(self.optimizer, total_iters=n_warmup)
        scheduler2 = torch.optim.lr_scheduler.StepLR(self.optimizer, 1, gamma=lr_decay)
        self.scheduler = torch.optim.lr_scheduler.SequentialLR(self.optimizer, schedulers=[scheduler1, scheduler2], milestones=[n_warmup])
        # self.scheduler = torch.optim.lr_scheduler.CyclicLR(self.optimizer, lr, 0.05, mode='triangular2', cycle_momentum=False, step_size_up=1000)
        self.criterion = nn.BCEWithLogitsLoss(reduction='none')
        self.checkpoint_path = checkpoint_path
        self.mask_gamma = mask_gamma
        
    def load_checkpoint(self):
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])
        
    def fit(self, epochs=20, batch_size=32, patience=10, loss_callback=None):        
        train_loader = DataLoader(self.train_dataset, batch_size=batch_size, shuffle=True, collate_fn=dp.pad_collate)
        val_loader = DataLoader(self.val_dataset, batch_size=batch_size, collate_fn=dp.pad_collate)
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
                    outputs = outputs.to(self.device)
                    weights = weights.to(self.device)
                    lengths = lengths.to(self.device)
                    preds = self.model(inputs)
                    if torch.isnan(preds).any():
                        print("Nan predictions", torch.isnan(inputs).sum(), lengths)
                    scaled_weights = torch.exp(weights / weight_temperature) / torch.sum(torch.where(weights > 0, torch.exp(weights / weight_temperature), 0.0))
                    loss = (self.criterion(preds.squeeze(-1), outputs) * (scaled_weights * (weights > 0).sum()))
                    # loss += self.change_lambda * torch.linalg.norm(shifted_inputs - inputs, 2, 2)
                    loss_mask = torch.arange(loss.shape[1]).to(self.device)[None, :] < lengths[:, None]
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
                        outputs = outputs.to(self.device)
                        weights = weights.to(self.device)
                        lengths = lengths.to(self.device)
                        preds = self.model(inputs)
                        scaled_weights = torch.exp(weights / weight_temperature) / torch.sum(torch.where(weights > 0, torch.exp(weights / weight_temperature), 0.0))
                        loss = (self.criterion(preds.squeeze(-1), outputs) * (scaled_weights * (weights > 0).sum()))
                        loss_mask = torch.arange(loss.shape[1]).to(self.device)[None, :] < lengths[:, None]
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
    
    def predict(self, batch_size=32, split='test'):
        self.model.eval()
        loader = DataLoader({
            'train': self.train_dataset, 
            'val': self.val_dataset,
            'test': self.test_dataset
        }[split], batch_size=batch_size, collate_fn=dp.pad_collate)
        with torch.no_grad():
            bar = tqdm.tqdm(loader)
            all_predictions = []
            for inputs, outputs, weights, lengths in bar:
                inputs = inputs.to(self.device)
                lengths = lengths.to(self.device)
                preds = self.model(inputs)
                all_predictions.append(np.concatenate([x[:l].cpu().numpy() for x, l in zip(preds, lengths)]))
        all_predictions = np.concatenate(all_predictions)
        return all_predictions
