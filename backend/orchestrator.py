from typing import Dict, Any, List
from agents import PlaintiffLawyer, DefendantLawyer, Judge
import asyncio


class DebateOrchestrator:
    """Orchestrates multi-agent debate simulation."""
    
    def __init__(self):
        self.plaintiff_lawyer = PlaintiffLawyer()
        self.defendant_lawyer = DefendantLawyer()
        self.judge = Judge()
    
    async def run_simulation(self, case_data: Dict[str, Any], rounds: int = 2) -> Dict[str, Any]:
        """Run multi-agent debate simulation."""
        
        facts = case_data.get('facts', '')
        issues = case_data.get('issues', '')
        holding = case_data.get('holding', '')
        
        debate_transcript = []
        
        # Run debate rounds
        for round_num in range(1, rounds + 1):
            # Plaintiff's argument
            plaintiff_context = {
                'facts': facts,
                'issues': issues,
                'holding': holding
            }
            
            plaintiff_arg = await self.plaintiff_lawyer.generate_response(plaintiff_context)
            debate_transcript.append({
                'round': round_num,
                'speaker': 'Plaintiff Lawyer',
                'argument': plaintiff_arg
            })
            
            # Defendant's counter-argument
            defendant_context = {
                'facts': facts,
                'issues': issues,
                'holding': holding
            }
            
            defendant_arg = await self.defendant_lawyer.generate_response(defendant_context)
            debate_transcript.append({
                'round': round_num,
                'speaker': 'Defendant Lawyer',
                'argument': defendant_arg
            })
        
        # Collect all arguments for judge
        plaintiff_arguments = '\n\n'.join([
            t['argument'] for t in debate_transcript if t['speaker'] == 'Plaintiff Lawyer'
        ])
        defendant_arguments = '\n\n'.join([
            t['argument'] for t in debate_transcript if t['speaker'] == 'Defendant Lawyer'
        ])
        
        # Judge renders verdict
        judge_context = {
            'facts': facts,
            'issues': issues,
            'holding': holding,
            'plaintiff_arguments': plaintiff_arguments,
            'defendant_arguments': defendant_arguments
        }
        
        verdict = await self.judge.render_verdict(judge_context)
        
        return {
            'debate_transcript': debate_transcript,
            'verdict': verdict,
            'rounds_completed': rounds
        }
