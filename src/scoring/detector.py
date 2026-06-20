from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

from .constants import DEEPFAKE_MODEL_ID


@dataclass
class DeepfakeModel:
    model: Any
    processor: Any
    model_id: str

    @property
    def version(self) -> str:
        revision = getattr(self.model.config, "_name_or_path", self.model_id)
        return f"{self.model_id}@{revision}"


_cached_model: DeepfakeModel | None = None


def get_deepfake_model() -> DeepfakeModel:
    global _cached_model
    if _cached_model is None:
        processor = AutoImageProcessor.from_pretrained(DEEPFAKE_MODEL_ID)
        model = AutoModelForImageClassification.from_pretrained(DEEPFAKE_MODEL_ID)
        model.eval()
        _cached_model = DeepfakeModel(
            model=model,
            processor=processor,
            model_id=DEEPFAKE_MODEL_ID,
        )
    return _cached_model


def predict_fake_probability(model_image) -> float:
    """Return synthetic-media probability in [0, 1] (1 = more likely fake/AI)."""
    return max(0.0, min(1.0, 1.0 - predict_authenticity_score(model_image)))


def predict_authenticity_score(model_image) -> float:
    """Return authenticity confidence in [0, 1] (1 = more likely real)."""
    bundle = get_deepfake_model()
    inputs = bundle.processor(images=model_image, return_tensors="pt")

    with torch.no_grad():
        outputs = bundle.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

    id2label = bundle.model.config.id2label
    fake_prob = 0.0
    for idx, label in id2label.items():
        label_lower = label.lower()
        if "fake" in label_lower or "deepfake" in label_lower or "ai" in label_lower:
            fake_prob = max(fake_prob, float(probs[int(idx)]))

    if fake_prob == 0.0 and len(probs) == 2:
        fake_prob = float(probs[1])

    return max(0.0, min(1.0, 1.0 - fake_prob))


def load_detector() -> DeepfakeModel:
    return get_deepfake_model()
