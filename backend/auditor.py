from typing import Dict, Any
from agents import Auditor


class BiasAuditor:
    """Performs bias auditing on case and verdict."""
    
    def __init__(self):
        self.auditor = Auditor()
    
    async def audit(self, case_data: Dict[str, Any], verdict: Dict[str, Any]) -> Dict[str, Any]:
        """Audit case for bias and fairness."""
        
        facts = case_data.get('facts', '')
        verdict_text = verdict.get('verdict', '')
        reasoning = ' '.join(verdict.get('reasoning', []))
        
        audit_context = {
            'facts': facts,
            'verdict': verdict_text,
            'reasoning': reasoning
        }
        
        audit_result = await self.auditor.audit_case(audit_context)
        
        return audit_result
