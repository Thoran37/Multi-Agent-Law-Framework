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
