import random
from typing import Dict, Any


class BaselineClassifier:
    """Simple baseline classifier for case outcome prediction."""
    
    def __init__(self):
        # Keywords that might indicate plaintiff favor
        self.plaintiff_keywords = [
            'violation', 'breach', 'negligence', 'damages', 'injury',
            'rights', 'compensation', 'liability', 'guilty', 'proved'
        ]
        
        # Keywords that might indicate defendant favor
        self.defendant_keywords = [
            'dismissed', 'lack of evidence', 'not proved', 'innocent',
            'compliance', 'proper procedure', 'no violation', 'acquitted'
        ]
    
    def predict(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict case outcome based on simple keyword analysis."""
        
        # Combine all text
        text = f"{case_data.get('facts', '')} {case_data.get('issues', '')} {case_data.get('holding', '')}"
        text_lower = text.lower()
        
        # Count keywords
        plaintiff_score = sum(1 for kw in self.plaintiff_keywords if kw in text_lower)
        defendant_score = sum(1 for kw in self.defendant_keywords if kw in text_lower)
        
        # Calculate confidence
        total_score = plaintiff_score + defendant_score
        if total_score > 0:
            plaintiff_confidence = (plaintiff_score / total_score) * 100
        else:
            # Random baseline if no keywords found
            plaintiff_confidence = 50 + random.uniform(-10, 10)
        
        # Determine prediction
        if plaintiff_confidence >= 50:
            prediction = "FAVOR_PLAINTIFF"
            confidence = plaintiff_confidence
        else:
            prediction = "FAVOR_DEFENDANT"
            confidence = 100 - plaintiff_confidence
        
        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "method": "baseline_keyword_classifier",
            "plaintiff_keywords_found": plaintiff_score,
            "defendant_keywords_found": defendant_score
        }
