from groq import AsyncGroq
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import re
import logging

# Optional local model imports
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    HAS_TRANSFORMERS = True
except Exception:
    HAS_TRANSFORMERS = False

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


def _load_prompt_file(agent_type: str) -> str:
    prompt_file = PROMPTS_DIR / f"{agent_type}.txt"
    if prompt_file.exists():
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


# Try to load local model from ./qwenn_model if available
LOCAL_MODEL_PATH = Path(__file__).parent.parent / "qwenn_model"
_local_tokenizer = None
_local_model = None
if HAS_TRANSFORMERS and LOCAL_MODEL_PATH.exists():
    try:
        _local_tokenizer = AutoTokenizer.from_pretrained(str(LOCAL_MODEL_PATH))
        _local_model = AutoModelForSeq2SeqLM.from_pretrained(str(LOCAL_MODEL_PATH))
        # ensure model in eval mode
        _local_model.eval()
        logger.info("Loaded local model from %s", LOCAL_MODEL_PATH)
    except Exception as e:
        logger.exception("Failed to load local model: %s", e)
        _local_tokenizer = None
        _local_model = None


class LegalAgent:
    """Base class for legal agents using Groq by default."""

    def __init__(self, agent_type: str):
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.agent_type = agent_type
        self.prompt_template = _load_prompt_file(agent_type)

    async def generate_response(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_template.format(**context)
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a {self.agent_type.replace('_', ' ')} in an Indian courtroom."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("Groq generation failed for %s: %s", self.agent_type, e)
            return f"Error generating response: {str(e)}"


class LocalLegalAgent(LegalAgent):
    """Agent that prefers the local model for generation (fallbacks to Groq)."""

    def __init__(self, agent_type: str):
        super().__init__(agent_type)

    async def generate_response(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_template.format(**context)

        # If local model not available, fallback to Groq
        if _local_model is None or _local_tokenizer is None:
            # logger.warning("Local model not available, falling back to Groq for %s", self.agent_type)
            return await super().generate_response(context)

        # Offload synchronous generation to threadpool
        loop = __import__('asyncio').get_running_loop()

        def _sync_generate(p: str) -> str:
            try:
                inputs = _local_tokenizer(p, return_tensors="pt", truncation=True, max_length=1024)
                with torch.no_grad():
                    outputs = _local_model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
                text = _local_tokenizer.decode(outputs[0], skip_special_tokens=True)
                return text.strip()
            except Exception as e:
                logger.exception("Local model generation error: %s", e)
                return f"Error generating response (local model): {str(e)}"

        return await loop.run_in_executor(None, _sync_generate, prompt)


class PlaintiffLawyer(LocalLegalAgent):
    def __init__(self):
        super().__init__("plaintiff_lawyer")


class DefendantLawyer(LocalLegalAgent):
    def __init__(self):
        super().__init__("defendant_lawyer")


class Judge(LegalAgent):
    def __init__(self):
        super().__init__("judge")

    async def render_verdict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured verdict using Groq (Judge remains Groq-driven)."""
        response_text = await self.generate_response(context)

        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                verdict = json.loads(json_match.group())
            else:
                verdict = json.loads(response_text)

            if 'verdict' in verdict and 'confidence' in verdict:
                return verdict
        except Exception:
            pass

        verdict_type = "FAVOR_PLAINTIFF" if "plaintiff" in response_text.lower() else "FAVOR_DEFENDANT"
        return {
            "verdict": verdict_type,
            "confidence": 75,
            "reasoning": [response_text[:200]],
            "supporting_evidence": ["Evidence from case facts"]
        }


class Auditor(LegalAgent):
    def __init__(self):
        super().__init__("auditor")

    async def audit_case(self, context: Dict[str, Any]) -> Dict[str, Any]:
        response_text = await self.generate_response(context)
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                audit_result = json.loads(json_match.group())
            else:
                audit_result = json.loads(response_text)

            if 'fairness_score' in audit_result:
                return audit_result
        except Exception:
            pass

        case_text = f"{context.get('facts', '')} {context.get('verdict', '')} {context.get('reasoning', '')}"
        return self._simple_bias_detection(case_text)

    def _simple_bias_detection(self, text: str) -> Dict[str, Any]:
        bias_keywords = {
            'gender': ['he', 'she', 'his', 'her', 'man', 'woman', 'male', 'female'],
            'regional': ['north', 'south', 'rural', 'urban', 'village'],
            'religious': ['hindu', 'muslim', 'christian', 'sikh'],
            'caste': ['caste', 'scheduled', 'tribe', 'backward']
        }

        text_lower = text.lower()
        found_biases = []
        bias_types = []

        for bias_type, keywords in bias_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if keyword not in found_biases:
                        found_biases.append(keyword)
                    if bias_type not in bias_types:
                        bias_types.append(bias_type)

        fairness_score = max(50, 100 - (len(found_biases) * 5))

        return {
            "fairness_score": fairness_score,
            "biased_terms": found_biases[:10],
            "bias_types": bias_types,
            "recommendations": [
                "Use gender-neutral language where possible",
                "Avoid stereotypical assumptions",
                "Focus on facts and legal precedents"
            ],
            "summary": f"Found {len(found_biases)} potentially biased terms. Fairness score: {fairness_score}/100"
        }
