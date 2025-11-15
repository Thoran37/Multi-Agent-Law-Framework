from groq import AsyncGroq
import os
from pathlib import Path
from typing import Dict, Any, List
import json
import re

PROMPTS_DIR = Path("/app/backend/prompts")


class LegalAgent:
    """Base class for legal agents."""
    
    def __init__(self, agent_type: str):
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.agent_type = agent_type
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load prompt template from file."""
        prompt_file = PROMPTS_DIR / f"{self.agent_type}.txt"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    async def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate response based on context."""
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
            return f"Error generating response: {str(e)}"


class PlaintiffLawyer(LegalAgent):
    def __init__(self):
        super().__init__("plaintiff_lawyer")


class DefendantLawyer(LegalAgent):
    def __init__(self):
        super().__init__("defendant_lawyer")


class Judge(LegalAgent):
    def __init__(self):
        super().__init__("judge")
    
    async def render_verdict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured verdict."""
        response_text = await self.generate_response(context)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                verdict = json.loads(json_match.group())
            else:
                verdict = json.loads(response_text)
            
            # Validate structure
            if 'verdict' in verdict and 'confidence' in verdict:
                return verdict
        except:
            pass
        
        # Fallback: create structured verdict from text
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
        """Perform bias audit on the case."""
        response_text = await self.generate_response(context)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                audit_result = json.loads(json_match.group())
            else:
                audit_result = json.loads(response_text)
            
            if 'fairness_score' in audit_result:
                return audit_result
        except:
            pass
        
        # Fallback: perform simple bias detection
        case_text = f"{context.get('facts', '')} {context.get('verdict', '')} {context.get('reasoning', '')}"
        return self._simple_bias_detection(case_text)
    
    def _simple_bias_detection(self, text: str) -> Dict[str, Any]:
        """Simple pattern-based bias detection."""
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
        
        # Calculate fairness score (higher = more fair)
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
