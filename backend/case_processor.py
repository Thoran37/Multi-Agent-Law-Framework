from groq import AsyncGroq
import os
import json
import re
from typing import Dict, Any


class CaseProcessor:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
    
    async def extract_case_details(self, case_text: str) -> Dict[str, Any]:
        """Extract facts, issues, and holding from case text using LLM."""
        
        prompt = f"""You are a legal AI assistant analyzing an Indian legal case document.

Case Document:
{case_text[:4000]}

Extract the following information from the case:
1. FACTS: Key facts and background of the case (3-5 sentences)
2. ISSUES: Main legal issues or questions presented (2-4 points)
3. HOLDING: The court's decision or main conclusions (2-3 sentences)

Provide your response in the following JSON format:
{{
  "facts": "facts text here",
  "issues": "issues text here",
  "holding": "holding text here"
}}

Only return valid JSON, no additional text."""
        
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a legal document analyzer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)
            
            return {
                "facts": result.get("facts", "Facts could not be extracted"),
                "issues": result.get("issues", "Issues could not be extracted"),
                "holding": result.get("holding", "Holding could not be extracted")
            }
            
        except Exception as e:
            # Fallback extraction
            return self._fallback_extraction(case_text)
    
    def _fallback_extraction(self, case_text: str) -> Dict[str, Any]:
        """Simple pattern-based extraction as fallback."""
        text_lower = case_text.lower()
        
        # Try to find facts section
        facts = "Facts not clearly identifiable in document."
        facts_patterns = [r'facts?[:\s]+([^\n]{100,500})', r'background[:\s]+([^\n]{100,500})']
        for pattern in facts_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                facts = match.group(1).strip()[:500]
                break
        
        # Try to find issues
        issues = "Legal issues not clearly specified."
        issues_patterns = [r'issues?[:\s]+([^\n]{50,400})', r'question[s]?[:\s]+([^\n]{50,400})']
        for pattern in issues_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                issues = match.group(1).strip()[:400]
                break
        
        # Try to find holding/judgment
        holding = "Holding/judgment not clearly specified."
        holding_patterns = [r'holding[:\s]+([^\n]{50,400})', r'judgment[:\s]+([^\n]{50,400})', r'decision[:\s]+([^\n]{50,400})']
        for pattern in holding_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                holding = match.group(1).strip()[:400]
                break
        
        return {
            "facts": facts,
            "issues": issues,
            "holding": holding
        }

    async def find_related_laws(self, case_text: str, jurisdiction: str) -> Dict[str, Any]:
        """Query the LLM for relevant laws, statutes, and citations for a jurisdiction.

        Returns a dict with a 'laws' list. Each item may be a string or structured dict
        depending on model output.
        """
        prompt = f"""You are a legal research assistant. Given the following case document and the specified jurisdiction, list the most relevant statutes, sections, or legal principles (with short citations if possible) that apply to the facts. For each item provide a one-line summary of why it is relevant.

Jurisdiction: {jurisdiction}

Case Document (first 3000 chars):
{case_text[:3000]}

Provide the response as a JSON object with a single key `laws` whose value is an array of objects with keys: `citation` and `summary`. If you cannot provide structured JSON, return a JSON object with `laws` as an array of strings."""

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a legal research assistant. Respond in JSON if possible."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()

            # Try to extract JSON
            import re, json
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)

            laws = result.get('laws', [])
            # Normalize: if laws are strings, wrap into dicts
            normalized = []
            for item in laws:
                if isinstance(item, str):
                    normalized.append({'citation': None, 'summary': item})
                elif isinstance(item, dict):
                    normalized.append({
                        'citation': item.get('citation') or item.get('name') or None,
                        'summary': item.get('summary') or item.get('reason') or json.dumps(item)
                    })
            return {'laws': normalized}

        except Exception as e:
            # Fallback: simple keyword-based heuristics (limited)
            fallback = []
            text = case_text.lower()
            if 'tenant' in text or 'landlord' in text:
                fallback.append({'citation': 'Local Tenancy Law', 'summary': 'Tenancy and landlord obligations relevant to repairs and access.'})
            if 'negligence' in text or 'injury' in text:
                fallback.append({'citation': 'Negligence Principles', 'summary': 'Elements of negligence and duties of care.'})
            if not fallback:
                fallback.append({'citation': None, 'summary': 'No clear statute identified; consider jurisdictional research.'})
            return {'laws': fallback}
