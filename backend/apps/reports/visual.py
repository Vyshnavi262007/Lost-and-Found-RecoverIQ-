"""OPTIONAL visual-similarity adapter.

Active ONLY if torch + torchvision are installed and the pretrained MobileNetV3 weights can be
loaded (see requirements-visual.txt and README). Otherwise `available()` is False and the
matching engine simply leaves the visual component out and renormalises the other weights.
This is real image-embedding cosine similarity; it never compares file names.
"""
import logging
import math

logger = logging.getLogger(__name__)
_state = {"checked": False, "model": None, "preprocess": None, "torch": None}


def _load():
    if _state["checked"]:
        return
    _state["checked"] = True
    try:
        import torch
        from torchvision import models
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        model = models.mobilenet_v3_small(weights=weights)
        model.classifier = torch.nn.Identity()
        model.eval()
        _state.update(model=model, preprocess=weights.transforms(), torch=torch)
    except Exception as exc:  # missing packages, no weights, no network, etc.
        logger.info("Visual similarity disabled: %s", exc)


def available():
    _load()
    return _state["model"] is not None


def embed_path(path):
    """Return an embedding list for an image file, or None."""
    if not available():
        return None
    try:
        from PIL import Image
        torch = _state["torch"]
        with Image.open(path) as img:
            x = _state["preprocess"](img.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            return _state["model"](x)[0].tolist()
    except Exception as exc:
        logger.warning("Could not embed image %s: %s", path, exc)
        return None


def cosine(u, v):
    if not u or not v or len(u) != len(v):
        return None
    dot = sum(a * b for a, b in zip(u, v))
    nu, nv = math.sqrt(sum(a * a for a in u)), math.sqrt(sum(b * b for b in v))
    return max(0.0, dot / (nu * nv)) if nu and nv else None
