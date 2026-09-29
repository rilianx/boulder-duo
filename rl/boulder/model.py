"""Transformer sobre tokens de entidades → política (5 acciones) y valor."""
from __future__ import annotations

import torch
from torch import nn

from .tokens import N_FEATURES


class EntityTransformer(nn.Module):
    def __init__(self, n_features=N_FEATURES, d=64, heads=4, layers=3, n_actions=5):
        super().__init__()
        self.embed = nn.Sequential(nn.Linear(n_features, d), nn.LayerNorm(d))
        layer = nn.TransformerEncoderLayer(d, heads, 2 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d)
        self.pi = nn.Linear(2 * d, n_actions)
        self.v = nn.Linear(2 * d, 1)
        nn.init.normal_(self.pi.weight, std=0.01)
        nn.init.zeros_(self.pi.bias)

    def forward(self, tokens: torch.Tensor, mask: torch.Tensor):
        """tokens [B, T, F] float, mask [B, T] bool (True = token válido; el 0 siempre lo es)."""
        h = self.encoder(self.embed(tokens), src_key_padding_mask=~mask)
        h = self.norm(h)
        m = mask.unsqueeze(-1).to(h.dtype)
        pooled = (h * m).sum(1) / m.sum(1).clamp_min(1)
        z = torch.cat([h[:, 0], pooled], -1)
        return self.pi(z), self.v(z).squeeze(-1)


class PointerTransformer(nn.Module):
    """La acción es un token: logits_i = q(propio + contexto) · k(token_i) / √d, con los inválidos enmascarados."""

    def __init__(self, n_features, d=64, heads=4, layers=3):
        super().__init__()
        self.embed = nn.Sequential(nn.Linear(n_features, d), nn.LayerNorm(d))
        layer = nn.TransformerEncoderLayer(d, heads, 2 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d)
        self.q = nn.Linear(2 * d, d)
        self.k = nn.Linear(d, d)
        self.v = nn.Linear(2 * d, 1)
        nn.init.normal_(self.q.weight, std=0.01)
        self.scale = d ** -0.5

    def forward(self, tokens, mask, valid):
        h = self.norm(self.encoder(self.embed(tokens), src_key_padding_mask=~mask))
        m = mask.unsqueeze(-1).to(h.dtype)
        z = torch.cat([h[:, 0], (h * m).sum(1) / m.sum(1).clamp_min(1)], -1)
        logits = torch.einsum("bd,btd->bt", self.q(z), self.k(h)) * self.scale
        logits = logits.masked_fill(~valid, -1e9)
        return logits, self.v(z).squeeze(-1)
