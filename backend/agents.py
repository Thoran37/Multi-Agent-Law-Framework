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
        # Build enriched context with debate history for proper formatting
        enriched_context = {
            'facts': context.get('facts', ''),
            'issues': context.get('issues', ''),
            'holding': context.get('holding', ''),
            'previous_debate': context.get('previous_debate', ''),
            'opponent_arguments': context.get('opponent_arguments', ''),
            'round_number': context.get('round_number', 1),
        }
        
        # Handle template formatting - use safe format to avoid KeyError
        try:
            prompt = self.prompt_template.format(**enriched_context)
        except KeyError:
            # Fallback: just use the template with basic context
            prompt = f"""Facts: {enriched_context['facts']}
Issues: {enriched_context['issues']}
Holding: {enriched_context['holding']}

{enriched_context['previous_debate']}
{enriched_context['opponent_arguments']}

Provide your legal argument for round {enriched_context['round_number']}."""
        
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a {self.agent_type.replace('_', ' ')} in an Indian courtroom. Respond directly to the opposing counsel's arguments and build your case based on the case facts and legal issues presented."},
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
        # Build enriched context with debate history for proper formatting
        enriched_context = {
            'facts': context.get('facts', ''),
            'issues': context.get('issues', ''),
            'holding': context.get('holding', ''),
            'previous_debate': context.get('previous_debate', ''),
            'opponent_arguments': context.get('opponent_arguments', ''),
            'round_number': context.get('round_number', 1),
        }
        
        # Handle template formatting - use safe format to avoid KeyError
        try:
            prompt = self.prompt_template.format(**enriched_context)
        except KeyError:
            # Fallback: just use the template with basic context
            prompt = f"""Facts: {enriched_context['facts']}
Issues: {enriched_context['issues']}
Holding: {enriched_context['holding']}

{enriched_context['previous_debate']}
{enriched_context['opponent_arguments']}

Provide your legal argument for round {enriched_context['round_number']}."""

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
        """Generate structured, decisive verdict with clear winner and penalty/remedy."""
        response_text = await self.generate_response(context)
        
        # Try to parse structured JSON response from judge
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                verdict = json.loads(json_match.group())
                if 'verdict' in verdict and 'reasoning' in verdict:
                    return self._normalize_verdict(verdict)
            else:
                verdict = json.loads(response_text)
                if 'verdict' in verdict:
                    return self._normalize_verdict(verdict)
        except Exception:
            pass

        # Parse response to determine winner and details
        return self._parse_judge_response(response_text, context)

    def _parse_judge_response(self, response_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse judge's natural language response into structured verdict."""
        text_lower = response_text.lower()
        
        # Determine verdict winner
        plaintiff_indicators = ['plaintiff prevails', 'plaintiff wins', 'favor plaintiff', 'favor the plaintiff', 'judgment for plaintiff']
        defendant_indicators = ['defendant prevails', 'defendant wins', 'favor defendant', 'favor the defendant', 'judgment for defendant']
        
        verdict_type = "PENDING"
        for indicator in plaintiff_indicators:
            if indicator in text_lower:
                verdict_type = "FAVOR_PLAINTIFF"
                break
        
        if verdict_type == "PENDING":
            for indicator in defendant_indicators:
                if indicator in text_lower:
                    verdict_type = "FAVOR_DEFENDANT"
                    break
        
        # If still pending, analyze debate arguments
        if verdict_type == "PENDING":
            plaintiff_args = context.get('plaintiff_arguments', '').lower()
            defendant_args = context.get('defendant_arguments', '').lower()
            
            # Simple heuristic: count positive indicators
            plaintiff_score = sum(1 for word in ['proved', 'evidence', 'liable', 'guilty', 'violation'] if word in plaintiff_args)
            defendant_score = sum(1 for word in ['proved', 'evidence', 'liable', 'guilty', 'violation'] if word in defendant_args)
            
            verdict_type = "FAVOR_PLAINTIFF" if plaintiff_score >= defendant_score else "FAVOR_DEFENDANT"
        
        # Extract penalty/damages from response
        penalty_info = self._extract_penalty_info(response_text, verdict_type)
        
        # Create concise 2-line summary
        summary_lines = self._create_verdict_summary(verdict_type, penalty_info, response_text)
        
        confidence = 85 if verdict_type != "PENDING" else 50
        
        return {
            "verdict": verdict_type,
            "confidence": confidence,
            "ruling": summary_lines[0],
            "remedy": summary_lines[1],
            "penalty_info": penalty_info,
            "reasoning": [response_text[:500]],
            "supporting_evidence": ["Analyzed debate arguments and case facts"],
            "full_reasoning": response_text
        }

    def _extract_penalty_info(self, text: str, verdict_type: str) -> Dict[str, Any]:
        """Extract penalty, damages, or jail time information from judge response."""
        import re
        
        penalty_info = {
            "type": "pending",
            "amount": None,
            "duration": None,
            "description": ""
        }
        
        # Look for monetary amounts
        money_pattern = r'(?:damages?|compensation|award|payment)\s*(?:of)?\s*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d{2})?)'
        money_match = re.search(money_pattern, text, re.IGNORECASE)
        if money_match:
            amount = money_match.group(1).replace(',', '')
            penalty_info["type"] = "monetary"
            penalty_info["amount"] = amount
            penalty_info["description"] = f"Pay ₹{amount} in damages"
        
        # Look for jail time
        jail_pattern = r'(?:imprisonment|jail|prison)\s+(?:of|for)?\s*(\d+)\s*(?:years?|months?|days?)'
        jail_match = re.search(jail_pattern, text, re.IGNORECASE)
        if jail_match:
            duration = jail_match.group(1)
            unit = re.search(r'(years?|months?|days?)', text, re.IGNORECASE)
            unit_str = unit.group(1) if unit else "months"
            penalty_info["type"] = "jail"
            penalty_info["duration"] = f"{duration} {unit_str}"
            penalty_info["description"] = f"Imprisonment for {duration} {unit_str}"
        
        # Look for other remedies
        if "compensate" in text.lower():
            penalty_info["description"] = penalty_info["description"] or "Provide compensation to plaintiff"
        if "specific performance" in text.lower():
            penalty_info["description"] = penalty_info["description"] or "Specific performance ordered"
        if "injunction" in text.lower():
            penalty_info["description"] = penalty_info["description"] or "Injunction issued"
        
        return penalty_info

    def _create_verdict_summary(self, verdict_type: str, penalty_info: Dict[str, Any], full_text: str) -> List[str]:
        """Create concise 2-line verdict summary."""
        
        # Line 1: Who won and why
        if verdict_type == "FAVOR_PLAINTIFF":
            line1 = "✓ VERDICT: Plaintiff prevails. Court finds the plaintiff's arguments supported by law and facts."
        elif verdict_type == "FAVOR_DEFENDANT":
            line1 = "✓ VERDICT: Defendant prevails. Court finds insufficient evidence supporting plaintiff's claims."
        else:
            line1 = "⚖ VERDICT: Case dismissed or inconclusive. Further evidence required."
        
        # Line 2: Remedy/Penalty
        if penalty_info.get("description"):
            line2 = f"REMEDY: {penalty_info['description']}"
        elif verdict_type == "FAVOR_PLAINTIFF":
            line2 = "REMEDY: Defendant ordered to cease violation and compensate plaintiff for damages."
        else:
            line2 = "REMEDY: Plaintiff's claims dismissed. No damages awarded."
        
        return [line1, line2]

    def _normalize_verdict(self, verdict: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize verdict structure from JSON response."""
        if "penalty_info" not in verdict:
            verdict["penalty_info"] = {
                "type": "pending",
                "amount": None,
                "duration": None,
                "description": verdict.get("remedy", "")
            }
        
        if "remedy" not in verdict:
            verdict["remedy"] = verdict.get("reasoning", [""])[0] if isinstance(verdict.get("reasoning"), list) else ""
        
        if "ruling" not in verdict:
            verdict["ruling"] = f"Court Rules: {verdict.get('verdict', 'PENDING')}"
        
        return verdict


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
