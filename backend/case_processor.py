from groq import AsyncGroq
import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class CaseProcessor:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.retriever = None
        self.llm = None
    
    def set_rag_chain(self, retriever, llm):
        """Set RAG retriever and LLM for case analysis."""
        self.retriever = retriever
        self.llm = llm
    
    async def extract_case_details(self, case_text: str) -> Dict[str, Any]:
        """Extract facts, issues, and holding from case text using RAG + LLM."""
        
        # If RAG is available, use it to enhance context
        if self.retriever and self.llm:
            return await self._extract_with_rag(case_text)
        else:
            return await self._extract_with_groq(case_text)
    
    async def _extract_with_rag(self, case_text: str) -> Dict[str, Any]:
        """Extract details using RAG for better context understanding."""
        try:
            loop = asyncio.get_running_loop()
            
            # Query RAG for facts, issues, and holdings
            queries = [
                "What are the key facts and background of this case?",
                "What are the main legal issues in this case?",
                "What is the court's decision or holding?"
            ]
            
            results = await asyncio.gather(*[
                loop.run_in_executor(None, self._query_rag_sync, query)
                for query in queries
            ])
            
            facts, issues, holding = results
            
            logger.info("Case details extracted using RAG")
            return {
                "facts": facts,
                "issues": issues,
                "holding": holding
            }
        except Exception as e:
            logger.warning(f"RAG extraction failed, falling back to Groq: {e}")
            return await self._extract_with_groq(case_text)
    
    def _query_rag_sync(self, query: str) -> str:
        """Synchronous wrapper for RAG query."""
        try:
            from langchain.chains import RetrievalQA
            from langchain.prompts import PromptTemplate
            
            prompt_template = """You are a legal expert. Answer the question using the provided legal documents.
If information is not found, provide a brief general answer.

Question: {question}

Answer:"""
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["question"]
            )
            
            rag_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.retriever,
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            result = rag_chain.invoke({"query": query})
            return result.get("result", "")
        except Exception as e:
            logger.exception(f"RAG query failed: {e}")
            return ""
    
    async def _extract_with_groq(self, case_text: str) -> Dict[str, Any]:
        """Extract details using Groq LLM (fallback)."""
        
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
        # render_page_image()
        
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
        prompt = f"""You are a legal research assistant specializing in {jurisdiction} law. Analyze the following case and provide EXACTLY 3-5 specific relevant laws, statutes, and legal principles that apply.

Case Document:
{case_text[:3000]}

RESPOND ONLY WITH VALID JSON (no other text):
{{"laws": [{{"citation": "Law Name/Section", "summary": "Why it applies"}}, ...]}}"""

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a legal research assistant. Respond ONLY with valid JSON, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=1500
            )

            content = response.choices[0].message.content.strip()
            logger.info(f"LLM response for laws: {content[:200]}")

            # Clean up response - remove markdown code blocks if present
            content = content.replace('```json', '').replace('```', '')
            
            # Try multiple JSON extraction strategies
            result = None
            
            # Strategy 1: Direct JSON parse
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Strategy 2: Extract JSON from response using regex
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass

            if result and isinstance(result, dict) and 'laws' in result:
                laws = result.get('laws', [])
                # Normalize: if laws are strings, wrap into dicts
                normalized = []
                for item in laws:
                    if isinstance(item, str):
                        normalized.append({'citation': 'General Legal Principle', 'summary': item})
                    elif isinstance(item, dict):
                        normalized.append({
                            'citation': item.get('citation') or item.get('name') or 'Applicable Law',
                            'summary': item.get('summary') or item.get('reason') or str(item)
                        })
                
                if normalized:
                    return {'laws': normalized}
            
            # If JSON extraction failed, fall through to keyword heuristics
            raise Exception("Could not parse LLM JSON response")

        except Exception as e:
            logger.warning(f"LLM law retrieval failed: {e}, using keyword heuristics")
            # Enhanced fallback: comprehensive keyword-based heuristics for Indian law
            fallback = []
            text = case_text.lower()
            
            # Contract and Commercial Law
            if any(k in text for k in ['contract', 'breach', 'agreement', 'sale', 'purchase', 'payment']):
                fallback.append({'citation': 'Indian Contract Act, 1872', 'summary': 'Applicable to formation, breach, and remedies for contractual disputes.'})
            
            # Negligence and Torts
            if any(k in text for k in ['negligence', 'injury', 'damage', 'accident', 'liability', 'fault']):
                fallback.append({'citation': 'Tort Law / Criminal Negligence', 'summary': 'Addresses duty of care, breach, causation, and compensatory damages.'})
            
            # Property and Tenancy
            if any(k in text for k in ['tenant', 'landlord', 'property', 'lease', 'rent', 'eviction', 'premises']):
                fallback.append({'citation': 'Transfer of Property Act, 1882 & Rent Control Laws', 'summary': 'Governs tenancy, eviction, rent disputes, and property rights.'})
            
            # Family Law
            if any(k in text for k in ['marriage', 'divorce', 'maintenance', 'custody', 'inheritance', 'succession', 'wife', 'child']):
                fallback.append({'citation': 'Indian Succession Act, 1925 & Family Laws', 'summary': 'Covers marriage, divorce, maintenance, custody, and inheritance.'})
            
            # Criminal Law
            if any(k in text for k in ['criminal', 'theft', 'assault', 'fraud', 'crime', 'guilty', 'innocent', 'police', 'arrest']):
                fallback.append({'citation': 'Indian Penal Code, 1860', 'summary': 'Defines criminal offenses and prescribes applicable punishments.'})
            
            # Labor Law
            if any(k in text for k in ['employee', 'employer', 'wage', 'labor', 'work', 'termination', 'working hours']):
                fallback.append({'citation': 'Industrial Disputes Act, 1947 & Labor Laws', 'summary': 'Covers employment, wages, working conditions, and dispute resolution.'})
            
            # Consumer Protection
            if any(k in text for k in ['consumer', 'product', 'quality', 'defect', 'refund', 'warranty']):
                fallback.append({'citation': 'Consumer Protection Act, 2019', 'summary': 'Protects consumer rights and provides remedies for product defects.'})
            
            # Taxation
            if any(k in text for k in ['tax', 'income', 'gst', 'duty', 'assessment', 'revenue']):
                fallback.append({'citation': 'Income Tax Act, 1961 / GST Law', 'summary': 'Governs taxation, assessment, and tax-related disputes.'})
            
            # Environmental and Public Law
            if any(k in text for k in ['environment', 'pollution', 'water', 'forest', 'waste', 'emissions']):
                fallback.append({'citation': 'Environmental Protection Act & Related Laws', 'summary': 'Addresses environmental protection and pollution control.'})
            
            # If still no matches, add a generic law
            if not fallback:
                fallback.append({'citation': 'Applicable Jurisdiction Law', 'summary': 'Relevant statutory provisions based on case facts and jurisdiction.'})
            
            return {'laws': fallback}
