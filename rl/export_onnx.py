"""Exporta la política entrenada a ONNX para correrla en el navegador (onnxruntime-web).

    python export_onnx.py --name base      # → rl/runs/base/policy.onnx
Entradas: tokens float32 [1, T, 91], mask bool [1, T] (T = max_tokens del entrenamiento, 32 por defecto). Salida: logits [1, 5].
"""
import argparse
from pathlib import Path

import torch

from boulder.model import EntityTransformer
from boulder.tokens import N_FEATURES


class Policy(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, tokens, mask):
        return self.m(tokens, mask)[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="base")
    a = p.parse_args()
    run = Path(__file__).parent / "runs" / a.name
    ck = torch.load(run / "ckpt.pt", weights_only=False)
    m = EntityTransformer(**ck["config"])
    m.load_state_dict(ck["model"]); m.eval()
    T = ck.get("max_tokens", 32)
    tok = torch.zeros(1, T, N_FEATURES)
    mask = torch.zeros(1, T, dtype=torch.bool); mask[0, :4] = True
    torch.onnx.export(Policy(m), (tok, mask), run / "policy.onnx", input_names=["tokens", "mask"],
                      output_names=["logits"], opset_version=17, dynamo=False)
    print("exportado", run / "policy.onnx")


if __name__ == "__main__":
    main()
