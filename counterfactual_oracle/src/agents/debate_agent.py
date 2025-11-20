"""
Debate Agent: Orchestrates multi-round debates between Gemini (Optimist) and DeepSeek (Skeptic)

This agent manages the debate flow, handles convergence detection, and synthesizes
the final consensus from the debate transcript.
"""

import time
import re
from typing import List, Tuple
import google.generativeai as genai
from openai import OpenAI

from ..models import FinancialReport, AggregatedSimulation, DebateTurn, DebateResult
from ..debate_prompts import (
    get_gemini_opening_prompt,
    get_deepseek_challenge_prompt,
    get_gemini_response_prompt,
    get_deepseek_counter_prompt,
    get_consensus_prompt,
    CONVERGENCE_ANALYSIS_PROMPT
)


from .validator import RealismValidatorAgent

class DebateAgent:
    def __init__(self, gemini_api_key: str, deepseek_api_key: str):
        """Initialize debate agent with API clients"""
        # Gemini (Optimist) - using gemini-2.0-flash-exp (latest available model)
        genai.configure(api_key=gemini_api_key)
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # DeepSeek (Skeptic)  
        self.deepseek = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        # Realism Validator
        self.validator = RealismValidatorAgent(api_key=gemini_api_key)
        
    def run_debate(
        self, 
        report: FinancialReport, 
        simulation: AggregatedSimulation,
        params: 'ScenarioParams',  # Add params for grounding
        max_rounds: int = 10,
        convergence_threshold: int = 2
    ) -> DebateResult:
        """
        Run a structured debate between Gemini and DeepSeek until convergence
        
        Args:
            report: Financial report data
            simulation: Simulation results
            params: Scenario parameters (for grounding to actual deltas)
            max_rounds: Maximum debate rounds (safety limit)
            convergence_threshold: Rounds without new objections needed for convergence
            
        Returns:
            DebateResult with complete transcript and consensus
        """
        debate_log = []
        convergence_counter = 0
        converged = False
        convergence_round = None
        
        # Round 1: Gemini opens with optimistic position (Validated)
        gemini_opening = self._get_validated_gemini_position(report, simulation, params, debate_log)
        debate_log.append(DebateTurn(
            round_number=1,
            speaker="Gemini",
            role="Optimist",
            message=gemini_opening,
            timestamp=time.time(),
            topic_focus="Opening Position"
        ))
        
        # Round 1: DeepSeek challenges
        deepseek_challenge = self._get_deepseek_challenge(gemini_opening, report, simulation, params, debate_log)
        debate_log.append(DebateTurn(
            round_number=1,
            speaker="DeepSeek",
            role="Skeptic",
            message=deepseek_challenge,
            timestamp=time.time(),
            topic_focus="Initial Challenge"
        ))
        
        # Continue debate until convergence or max rounds
        for round_num in range(2, max_rounds + 1):
            # Gemini responds to critique (Validated)
            gemini_response = self._get_validated_gemini_response(
                deepseek_challenge, 
                round_num, 
                debate_log,
                report,
                simulation,
                params
            )
            debate_log.append(DebateTurn(
                round_number=round_num,
                speaker="Gemini",
                role="Optimist",
                message=gemini_response,
                timestamp=time.time(),
                topic_focus=f"Round {round_num} Response"
            ))
            
            # Check for convergence
            if self._check_convergence(debate_log):
                convergence_counter += 1
                if convergence_counter >= convergence_threshold:
                    converged = True
                    convergence_round = round_num
                    break
            else:
                convergence_counter = 0  # Reset if new objections arise
            
            # DeepSeek counters
            deepseek_counter = self._get_deepseek_counter(
                gemini_response,
                round_num,
                debate_log
            )
            debate_log.append(DebateTurn(
                round_number=round_num,
                speaker="DeepSeek",
                role="Skeptic",
                message=deepseek_counter,
                timestamp=time.time(),
                topic_focus=f"Round {round_num} Counter"
            ))
            
            # Update for next iteration
            deepseek_challenge = deepseek_counter
        
        # Synthesize consensus
        consensus = self._synthesize_consensus(debate_log, converged)
        
        return DebateResult(
            debate_log=debate_log,
            total_rounds=len(set(t.round_number for t in debate_log)),
            converged=converged,
            convergence_round=convergence_round,
            consensus_summary=consensus['summary'],
            key_agreements=consensus['agreements'],
            key_disagreements=consensus['disagreements'],
            final_verdict=consensus['verdict'],
            confidence_level=consensus['confidence']
        )
    
    def _get_validated_gemini_position(
        self, 
        report: FinancialReport, 
        simulation: AggregatedSimulation,
        params: 'ScenarioParams',
        debate_log: List[DebateTurn]
    ) -> str:
        """Get Gemini's opening position with validation retry loop"""
        prompt = get_gemini_opening_prompt(report, simulation, params)
        
        for attempt in range(3):
            response = self.gemini.generate_content(prompt)
            text = response.text
            
            # Validate
            validation = self.validator.validate_statement(text, report, simulation)
            
            if validation['is_valid']:
                return text
            else:
                # Add feedback to prompt and retry
                prompt += f"\n\n[SYSTEM FEEDBACK]: Your previous response was rejected. Issues: {validation['issues']}. \nFeedback: {validation['feedback']}\n\nPlease rewrite strictly adhering to the data."
        
        return text # Return last attempt if all fail

    def _get_validated_gemini_response(
        self,
        deepseek_challenge: str,
        round_num: int,
        debate_log: List[DebateTurn],
        report: FinancialReport,
        simulation: AggregatedSimulation,
        params: 'ScenarioParams'
    ) -> str:
        """Get Gemini's response with validation retry loop"""
        # Summarize previous Gemini statements
        gemini_summary = " ".join([
            t.message[:100] for t in debate_log 
            if t.speaker == "Gemini"
        ])
        
        context = {'gemini_summary': gemini_summary}
        prompt = get_gemini_response_prompt(deepseek_challenge, round_num, context)
        
        for attempt in range(3):
            response = self.gemini.generate_content(prompt)
            text = response.text
            
            # Validate
            validation = self.validator.validate_statement(text, report, simulation)
            
            if validation['is_valid']:
                return text
            else:
                # Add feedback to prompt and retry
                prompt += f"\n\n[SYSTEM FEEDBACK]: Your previous response was rejected. Issues: {validation['issues']}. \nFeedback: {validation['feedback']}\n\nPlease rewrite strictly adhering to the data."
                
        return text
    
    def _get_deepseek_challenge(
        self,
        gemini_position: str,
        report: FinancialReport,
        simulation: AggregatedSimulation,
        params: 'ScenarioParams',
        debate_log: List[DebateTurn]
    ) -> str:
        """Get DeepSeek's challenge"""
        prompt = get_deepseek_challenge_prompt(gemini_position, report, simulation, params)
        response = self.deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def _get_deepseek_counter(
        self,
        gemini_response: str,
        round_num: int,
        debate_log: List[DebateTurn]
    ) -> str:
        """Get DeepSeek's counter-argument"""
        # Summarize previous DeepSeek statements
        deepseek_summary = " ".join([
            t.message[:100] for t in debate_log 
            if t.speaker == "DeepSeek"
        ])
        
        context = {'deepseek_summary': deepseek_summary}
        prompt = get_deepseek_counter_prompt(gemini_response, round_num, context)
        
        response = self.deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def _check_convergence(self, debate_log: List[DebateTurn]) -> bool:
        """
        Check if the debate has converged
        
        Convergence indicators:
        - Both agents use agreement language ("I agree", "You're right")
        - No new objections in last 2 turns
        - Similar conclusions being drawn
        """
        if len(debate_log) < 4:
            return False
        
        # Get last 2 messages from each agent
        recent_messages = [t.message.lower() for t in debate_log[-4:]]
        
        # Check for agreement keywords
        agreement_keywords = [
            "i agree", "you're right", "fair point", "i concede",
            "that makes sense", "good point", "i accept", "converge",
            "consensus", "we agree", "aligned"
        ]
        
        agreement_count = sum(
            1 for msg in recent_messages 
            for keyword in agreement_keywords 
            if keyword in msg
        )
        
        # If 2+ agreement statements in last 4 messages, likely converging
        return agreement_count >= 2
    
    def _synthesize_consensus(
        self, 
        debate_log: List[DebateTurn],
        converged: bool
    ) -> dict:
        """Synthesize final consensus from debate"""
        # Get final statements from both
        final_gemini = [t for t in debate_log if t.speaker == "Gemini"][-1].message
        final_deepseek = [t for t in debate_log if t.speaker == "DeepSeek"][-1].message
        
        # Extract agreements and disagreements
        agreements = self._extract_agreements(debate_log)
        disagreements = self._extract_disagreements(debate_log)
        
        # Determine verdict
        verdict = self._determine_verdict(debate_log, converged)
        
        # Determine confidence
        confidence = "High" if converged and len(disagreements) == 0 else \
                    "Medium" if converged else "Low"
        
        # Create summary
        summary = f"""After {len(set(t.round_number for t in debate_log))} rounds of debate, 
the analysts {'reached consensus' if converged else 'discussed but did not fully converge'}.

Key Points of Agreement:
{chr(10).join('- ' + a for a in agreements[:3])}

{'Remaining Concerns:' if disagreements else ''}
{chr(10).join('- ' + d for d in disagreements[:2]) if disagreements else ''}

Final Assessment: {verdict}
"""
        
        return {
            'summary': summary,
            'agreements': agreements,
            'disagreements': disagreements,
            'verdict': verdict,
            'confidence': confidence
        }
    
    def _extract_agreements(self, debate_log: List[DebateTurn]) -> List[str]:
        """Extract points of agreement from debate"""
        agreements = []
        
        for turn in debate_log:
            msg = turn.message
            msg_lower = msg.lower()
            
            # Find agreement keywords
            agreement_keywords = ["i agree", "you're right", "fair point", "i concede", "that makes sense"]
            
            for keyword in agreement_keywords:
                if keyword in msg_lower:
                    # Find the position of the keyword
                    keyword_pos = msg_lower.find(keyword)
                    
                    # Find the start of the sentence (look backwards for period or start of string)
                    start = msg.rfind('.', 0, keyword_pos) + 1
                    if start == 0:  # No period found, start from beginning
                        start = 0
                    
                    # Find the end of the sentence (look forwards for period)
                    end = msg.find('.', keyword_pos)
                    if end == -1:  # No period found, go to end
                        end = len(msg)
                    else:
                        end += 1  # Include the period
                    
                    # Extract the full sentence
                    sentence = msg[start:end].strip()
                    
                    # Only add if it's meaningful (more than 20 chars)
                    if len(sentence) > 20:
                        agreements.append(sentence)
                        break  # Only one agreement per turn
        
        # Return unique agreements
        unique_agreements = list(dict.fromkeys(agreements))  # Preserve order
        return unique_agreements[:5]
    
    def _extract_disagreements(self, debate_log: List[DebateTurn]) -> List[str]:
        """Extract remaining points of disagreement"""
        disagreements = []
        
        # Look at last 2 rounds
        recent_turns = [t for t in debate_log if t.round_number >= debate_log[-1].round_number - 1]
        
        for turn in recent_turns:
            msg = turn.message
            msg_lower = msg.lower()
            
            # Find disagreement keywords
            disagreement_keywords = ["however", "concern", "risk", "challenge", "but"]
            
            for keyword in disagreement_keywords:
                if keyword in msg_lower:
                    # Find the position of the keyword
                    keyword_pos = msg_lower.find(keyword)
                    
                    # Find the start of the sentence
                    start = msg.rfind('.', 0, keyword_pos) + 1
                    if start == 0:
                        start = 0
                    
                    # Find the end of the sentence
                    end = msg.find('.', keyword_pos)
                    if end == -1:
                        end = len(msg)
                    else:
                        end += 1
                    
                    # Extract the full sentence
                    sentence = msg[start:end].strip()
                    
                    # Only add if meaningful (more than 25 chars)
                    if len(sentence) > 25:
                        disagreements.append(sentence)
                        break
        
        # Return unique disagreements
        unique_disagreements = list(dict.fromkeys(disagreements))
        return unique_disagreements[:3]
    
    def _determine_verdict(self, debate_log: List[DebateTurn], converged: bool) -> str:
        """Determine final investment verdict from debate"""
        # Get all messages
        all_text = " ".join([t.message.lower() for t in debate_log])
        
        # Count positive vs negative sentiment
        positive_keywords = ["growth", "strong", "opportunity", "upside", "buy", "positive", "confident"]
        negative_keywords = ["risk", "concern", "downside", "sell", "negative", "weak", "challenge"]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in all_text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in all_text)
        
        # Determine verdict based on balance
        if positive_count > negative_count * 1.5:
            return "Buy" if converged else "Cautious Buy"
        elif negative_count > positive_count * 1.5:
            return "Sell" if converged else "Cautious Sell"
        else:
            return "Hold"
