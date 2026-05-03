from typing import Dict, Any, List
from .agents import PlaintiffLawyer, DefendantLawyer, Judge
import asyncio


class DebateOrchestrator:
    """Orchestrates multi-agent debate simulation."""
    
    def __init__(self):
        self.plaintiff_lawyer = PlaintiffLawyer()
        self.defendant_lawyer = DefendantLawyer()
        self.judge = Judge()
    
    def _get_previous_arguments(self, debate_transcript: List[Dict[str, Any]], speaker: str) -> str:
        """Get all previous arguments from the opponent."""
        opponent = "Defendant Lawyer" if speaker == "Plaintiff Lawyer" else "Plaintiff Lawyer"
        opponent_args = [
            t['argument'] for t in debate_transcript if t['speaker'] == opponent
        ]
        
        if not opponent_args:
            return ""
        
        formatted_args = "\n\n".join([
            f"[Round {i+1}] {opponent}: {arg}" 
            for i, arg in enumerate(opponent_args)
        ])
        return f"Previous opponent arguments:\n{formatted_args}"
    
    def _format_debate_history(self, debate_transcript: List[Dict[str, Any]]) -> str:
        """Format entire debate history for context."""
        if not debate_transcript:
            return ""
        
        history = "Previous debate history:\n"
        for entry in debate_transcript:
            history += f"[Round {entry['round']}] {entry['speaker']}: {entry['argument']}\n\n"
        return history
    
    async def run_simulation(self, case_data: Dict[str, Any], max_rounds: int = 4, min_rounds: int = 3) -> Dict[str, Any]:
        """Run multi-agent debate simulation with agents responding to each other.
        
        Args:
            case_data: The case information
            max_rounds: Maximum number of debate rounds (default 4)
            min_rounds: Minimum rounds to run (default 3)
        """
        
        facts = case_data.get('facts', '')
        issues = case_data.get('issues', '')
        holding = case_data.get('holding', '')
        
        debate_transcript = []
        
        # Run debate rounds dynamically
        for round_num in range(1, max_rounds + 1):
            # Plaintiff's argument - includes previous opponent arguments
            previous_opponent_args = self._get_previous_arguments(debate_transcript, "Plaintiff Lawyer")
            debate_history = self._format_debate_history(debate_transcript) if round_num > 1 else ""
            
            plaintiff_context = {
                'facts': facts,
                'issues': issues,
                'holding': holding,
                'previous_debate': debate_history,
                'opponent_arguments': previous_opponent_args,
                'round_number': round_num
            }
            
            plaintiff_arg = await self.plaintiff_lawyer.generate_response(plaintiff_context)
            debate_transcript.append({
                'round': round_num,
                'speaker': 'Plaintiff Lawyer',
                'argument': plaintiff_arg
            })
            
            # Defendant's counter-argument - includes previous plaintiff argument from this round
            previous_opponent_args = self._get_previous_arguments(debate_transcript, "Defendant Lawyer")
            debate_history = self._format_debate_history(debate_transcript)
            
            defendant_context = {
                'facts': facts,
                'issues': issues,
                'holding': holding,
                'previous_debate': debate_history,
                'opponent_arguments': previous_opponent_args,
                'round_number': round_num
            }
            
            defendant_arg = await self.defendant_lawyer.generate_response(defendant_context)
            debate_transcript.append({
                'round': round_num,
                'speaker': 'Defendant Lawyer',
                'argument': defendant_arg
            })
            
            # Stop early if we've reached min rounds and debate seems to be converging
            # (or continue until max_rounds)
            if round_num >= min_rounds and round_num < max_rounds:
                # Simple heuristic: if arguments are getting shorter, debate may be converging
                if len(defendant_arg) < 50:
                    break
        
        # Collect all arguments for judge
        plaintiff_arguments = '\n\n'.join([
            t['argument'] for t in debate_transcript if t['speaker'] == 'Plaintiff Lawyer'
        ])
        defendant_arguments = '\n\n'.join([
            t['argument'] for t in debate_transcript if t['speaker'] == 'Defendant Lawyer'
        ])
        
        # Format debate for judge's reference
        full_debate = '\n\n'.join([
            f"[Round {t['round']}] {t['speaker']}: {t['argument']}"
            for t in debate_transcript
        ])
        
        # Judge renders verdict
        judge_context = {
            'facts': facts,
            'issues': issues,
            'holding': holding,
            'plaintiff_arguments': plaintiff_arguments,
            'defendant_arguments': defendant_arguments,
            'full_debate': full_debate,
            'total_rounds': len(debate_transcript) // 2
        }
        
        verdict = await self.judge.render_verdict(judge_context)
        
        return {
            'debate_transcript': debate_transcript,
            'verdict': verdict,
            'rounds_completed': len(debate_transcript) // 2
        }
