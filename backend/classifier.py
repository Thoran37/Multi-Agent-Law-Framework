import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Try to import transformers for better classification
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class BaselineClassifier:
    """Enhanced classifier with both keyword analysis and zero-shot classification fallback."""
    
    def __init__(self):
        # Keywords that might indicate plaintiff favor
        self.plaintiff_keywords = [
            'violation', 'breach', 'negligence', 'damages', 'injury',
            'rights', 'compensation', 'liability', 'guilty', 'proved',
            'breach of contract', 'wrongful', 'unlawful', 'breach of duty',
            'tort', 'trespass', 'defamation'
        ]
        
        # Keywords that might indicate defendant favor
        self.defendant_keywords = [
            'dismissed', 'lack of evidence', 'not proved', 'innocent',
            'compliance', 'proper procedure', 'no violation', 'acquitted',
            'not liable', 'lawful', 'justified', 'valid', 'no breach',
            'reasonable', 'due diligence'
        ]
        
        # Initialize zero-shot classifier if available
        self.zero_shot_classifier = None
        if HAS_TRANSFORMERS:
            try:
                self.zero_shot_classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1  # CPU, change to 0 for GPU
                )
                logger.info("Loaded zero-shot classifier for case prediction")
            except Exception as e:
                logger.warning(f"Could not load zero-shot classifier: {e}. Using keyword fallback.")
                self.zero_shot_classifier = None
    
    def predict(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict case outcome using hybrid approach: zero-shot + keywords."""
        
        # Combine all text
        text = f"{case_data.get('facts', '')} {case_data.get('issues', '')} {case_data.get('holding', '')}"
        
        if not text.strip():
            return self._default_prediction()
        
        # Try zero-shot classification first (better semantic understanding)
        if self.zero_shot_classifier:
            try:
                zero_shot_result = self._predict_with_zero_shot(text)
                if zero_shot_result:
                    return zero_shot_result
            except Exception as e:
                logger.warning(f"Zero-shot classification failed: {e}. Falling back to keywords.")
        
        # Fallback to keyword-based classification
        return self._predict_with_keywords(text)
    
    def _predict_with_zero_shot(self, text: str) -> Dict[str, Any]:
        """Use zero-shot classification for semantic understanding."""
        try:
            # Define candidate labels for case outcome
            candidate_labels = [
                "plaintiff should win with significant damages",
                "defendant should win with no liability",
                "case is unclear or needs more evidence"
            ]
            
            # Truncate text to reasonable length for classification
            text_truncated = text[:1024]
            
            result = self.zero_shot_classifier(text_truncated, candidate_labels)
            
            top_label = result['labels'][0]
            confidence = result['scores'][0] * 100
            
            # Map zero-shot result to verdict
            if "plaintiff" in top_label.lower():
                return {
                    "prediction": "FAVOR_PLAINTIFF",
                    "confidence": round(min(confidence, 95), 2),
                    "method": "zero_shot_classifier",
                    "reasoning": top_label
                }
            elif "defendant" in top_label.lower():
                return {
                    "prediction": "FAVOR_DEFENDANT",
                    "confidence": round(min(confidence, 95), 2),
                    "method": "zero_shot_classifier",
                    "reasoning": top_label
                }
            else:
                # Unclear result, let keyword classifier handle it
                return None
                
        except Exception as e:
            logger.warning(f"Zero-shot classification error: {e}")
            return None
    
    def _predict_with_keywords(self, text: str) -> Dict[str, Any]:
        """Fallback: predict case outcome based on keyword analysis."""
        
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
            "method": "keyword_classifier",
            "plaintiff_keywords_found": plaintiff_score,
            "defendant_keywords_found": defendant_score
        }
    
    def _default_prediction(self) -> Dict[str, Any]:
        """Return default prediction when no text is available."""
        return {
            "prediction": "FAVOR_DEFENDANT",
            "confidence": 50.0,
            "method": "default",
            "reasoning": "Insufficient case data for prediction"
        }
