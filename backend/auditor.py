from typing import Dict, Any
from .agents import Auditor
import logging

logger = logging.getLogger(__name__)


class BiasAuditor:
    """Performs comprehensive bias auditing, fairness checks, and logical consistency validation on verdicts."""
    
    def __init__(self):
        self.auditor = Auditor()
    
    async def audit(self, case_data: Dict[str, Any], verdict: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive audit of case verdict for bias, fairness, and logical consistency."""
        
        facts = case_data.get('facts', '')
        issues = case_data.get('issues', '')
        verdict_text = verdict.get('verdict', '')
        ruling = verdict.get('ruling', '')
        remedy = verdict.get('remedy', '')
        reasoning = ' '.join(verdict.get('reasoning', []))
        penalty_info = verdict.get('penalty_info', {})
        
        # Build comprehensive audit context
        audit_context = {
            'facts': facts,
            'issues': issues,
            'verdict': verdict_text,
            'ruling': ruling,
            'remedy': remedy,
            'reasoning': reasoning,
            'penalty_info': str(penalty_info)
        }
        
        # Get LLM-based audit from Auditor agent
        llm_audit = await self.auditor.audit_case(audit_context)
        
        # Perform structural audits
        consistency_audit = self._check_verdict_consistency(facts, verdict_text, reasoning, remedy)
        proportionality_audit = self._check_remedy_proportionality(remedy, penalty_info, facts, issues)
        procedural_audit = self._check_procedural_fairness(ruling, reasoning, facts)
        
        # Combine all audit results
        combined_audit = {
            "overall_fairness_score": self._calculate_overall_score(llm_audit, consistency_audit, proportionality_audit, procedural_audit),
            "llm_bias_audit": llm_audit,
            "consistency_check": consistency_audit,
            "proportionality_check": proportionality_audit,
            "procedural_check": procedural_audit,
            "audit_summary": self._generate_audit_summary(llm_audit, consistency_audit, proportionality_audit, procedural_audit),
            "recommendations": self._generate_recommendations(llm_audit, consistency_audit, proportionality_audit, procedural_audit)
        }
        
        return combined_audit
    
    def _check_verdict_consistency(self, facts: str, verdict: str, reasoning: str, remedy: str) -> Dict[str, Any]:
        """Check if verdict is logically consistent with facts and reasoning."""
        issues = {
            "verdict_supported_by_reasoning": True,
            "remedy_matches_verdict": True,
            "all_facts_considered": True,
            "contradictions_found": []
        }
        
        facts_lower = facts.lower()
        reasoning_lower = reasoning.lower()
        remedy_lower = remedy.lower()
        verdict_lower = verdict.lower()
        
        # Check if verdict type appears in reasoning
        if "favor_plaintiff" in verdict_lower:
            if not any(word in reasoning_lower for word in ["plaintiff", "claimant", "petitioner", "proved", "evidence"]):
                issues["verdict_supported_by_reasoning"] = False
                issues["contradictions_found"].append("Verdict favors plaintiff but reasoning doesn't adequately support it")
        
        # Check if remedy is appropriate for verdict
        if "remedy" not in remedy_lower and "compensation" not in remedy_lower and "order" not in remedy_lower:
            if "favor_plaintiff" in verdict_lower:
                issues["remedy_matches_verdict"] = False
                issues["contradictions_found"].append("Plaintiff wins but no remedy/compensation specified")
        
        # Check if key facts from case appear in reasoning
        key_fact_keywords = ["case", "facts", "evidence", "argument", "law"]
        facts_mentioned = sum(1 for kw in key_fact_keywords if kw in reasoning_lower)
        if facts_mentioned < 2:
            issues["all_facts_considered"] = False
            issues["contradictions_found"].append("Reasoning does not adequately reference case facts or evidence")
        
        consistency_score = 100
        for issue in ["verdict_supported_by_reasoning", "remedy_matches_verdict", "all_facts_considered"]:
            if not issues[issue]:
                consistency_score -= 25
        
        issues["consistency_score"] = max(0, consistency_score)
        return issues
    
    def _check_remedy_proportionality(self, remedy: str, penalty_info: Dict[str, Any], facts: str, issues: str) -> Dict[str, Any]:
        """Check if remedy/penalty is proportionate to the case severity."""
        
        proportionality = {
            "is_proportionate": True,
            "severity_assessment": "moderate",
            "concerns": [],
            "proportionality_score": 100
        }
        
        # Assess case severity based on facts
        severe_keywords = ["serious", "death", "permanent", "severe", "aggravated", "repeated", "intentional"]
        minor_keywords = ["minor", "technical", "procedural", "administrative"]
        
        severity_count_high = sum(1 for kw in severe_keywords if kw in facts.lower())
        severity_count_low = sum(1 for kw in minor_keywords if kw in facts.lower())
        
        if severity_count_high > severity_count_low:
            proportionality["severity_assessment"] = "severe"
        elif severity_count_low > severity_count_high:
            proportionality["severity_assessment"] = "minor"
        else:
            proportionality["severity_assessment"] = "moderate"
        
        # Check remedy appropriateness
        remedy_lower = remedy.lower()
        
        if proportionality["severity_assessment"] == "severe":
            if not any(word in remedy_lower for word in ["significant", "substantial", "imprisonment", "year"]):
                proportionality["is_proportionate"] = False
                proportionality["concerns"].append("Severe case warrants stronger remedy")
                proportionality["proportionality_score"] -= 30
        
        elif proportionality["severity_assessment"] == "minor":
            if any(word in remedy_lower for word in ["imprisonment", "years", "heavy", "severe"]):
                proportionality["is_proportionate"] = False
                proportionality["concerns"].append("Minor case has disproportionately harsh remedy")
                proportionality["proportionality_score"] -= 30
        
        return proportionality
    
    def _check_procedural_fairness(self, ruling: str, reasoning: str, facts: str) -> Dict[str, Any]:
        """Check if the verdict followed fair procedural standards."""
        
        procedural = {
            "has_clear_reasoning": True,
            "considers_both_sides": True,
            "based_on_facts": True,
            "fairness_score": 100,
            "issues": []
        }
        
        reasoning_lower = reasoning.lower()
        ruling_lower = ruling.lower()
        facts_lower = facts.lower()
        
        # Check for clear reasoning
        if len(reasoning) < 50:
            procedural["has_clear_reasoning"] = False
            procedural["issues"].append("Ruling lacks sufficient reasoning")
            procedural["fairness_score"] -= 20
        
        # Check if both sides are considered
        both_sides_keywords = ["plaintiff", "defendant", "respondent", "petitioner", "both", "each"]
        sides_considered = sum(1 for kw in both_sides_keywords if kw in reasoning_lower)
        if sides_considered < 2:
            procedural["considers_both_sides"] = False
            procedural["issues"].append("Reasoning does not adequately address both parties' positions")
            procedural["fairness_score"] -= 25
        
        # Check if based on facts
        fact_keywords = ["fact", "evidence", "proved", "shown", "demonstrate", "establish"]
        fact_references = sum(1 for kw in fact_keywords if kw in reasoning_lower)
        if fact_references < 2:
            procedural["based_on_facts"] = False
            procedural["issues"].append("Ruling appears to lack evidentiary basis")
            procedural["fairness_score"] -= 20
        
        return procedural
    
    def _calculate_overall_score(self, llm_audit: Dict[str, Any], consistency: Dict[str, Any], 
                                  proportionality: Dict[str, Any], procedural: Dict[str, Any]) -> int:
        """Calculate overall fairness score from all audit components."""
        
        scores = [
            llm_audit.get("fairness_score", 75),
            consistency.get("consistency_score", 75),
            proportionality.get("proportionality_score", 75),
            procedural.get("fairness_score", 75)
        ]
        
        overall = sum(scores) // len(scores)
        return max(0, min(100, overall))
    
    def _generate_audit_summary(self, llm_audit: Dict[str, Any], consistency: Dict[str, Any], 
                                proportionality: Dict[str, Any], procedural: Dict[str, Any]) -> str:
        """Generate human-readable audit summary."""
        
        summary_parts = []
        
        # LLM bias audit summary
        if llm_audit.get("summary"):
            summary_parts.append(f"Bias Analysis: {llm_audit['summary']}")
        
        # Consistency summary
        if not consistency.get("verdict_supported_by_reasoning"):
            summary_parts.append("⚠️ Consistency Issue: Verdict reasoning is incomplete")
        
        # Proportionality summary
        if not proportionality.get("is_proportionate"):
            for concern in proportionality.get("concerns", []):
                summary_parts.append(f"⚠️ Proportionality: {concern}")
        
        # Procedural summary
        if not procedural.get("considers_both_sides"):
            summary_parts.append("⚠️ Procedural Concern: Both parties' arguments not adequately considered")
        
        if summary_parts:
            return " ".join(summary_parts)
        else:
            return "✓ Audit passed: No significant fairness concerns identified"
    
    def _generate_recommendations(self, llm_audit: Dict[str, Any], consistency: Dict[str, Any], 
                                   proportionality: Dict[str, Any], procedural: Dict[str, Any]) -> list:
        """Generate specific recommendations to improve fairness."""
        
        recommendations = []
        
        # From LLM audit
        recommendations.extend(llm_audit.get("recommendations", []))
        
        # From consistency check
        if consistency.get("contradictions_found"):
            recommendations.extend([f"Fix: {issue}" for issue in consistency["contradictions_found"]])
        
        # From proportionality check
        if proportionality.get("concerns"):
            recommendations.extend([f"Reconsider: {concern}" for concern in proportionality["concerns"]])
        
        # From procedural check
        if procedural.get("issues"):
            recommendations.extend([f"Improve: {issue}" for issue in procedural["issues"]])
        
        # Remove duplicates and limit
        recommendations = list(dict.fromkeys(recommendations))[:5]
        
        if not recommendations:
            recommendations = ["Verdict appears fair and well-reasoned"]
        
        return recommendations
