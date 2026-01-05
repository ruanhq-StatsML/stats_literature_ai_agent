"""LLM Alignment Agent - Simplest alignment procedures.

This module implements the simplest LLM alignment methods:
1. SFT (Supervised Fine-Tuning) - Fine-tune on preferred responses
2. DPO (Direct Preference Optimization) - Train on preference pairs without reward model
3. Best-of-N Sampling - Sample multiple responses and select the best

References:
- DPO: Rafailov et al. (2023) "Direct Preference Optimization: Your Language Model is Secretly a Reward Model"
- SFT: Standard supervised fine-tuning on high-quality demonstrations
- Constitutional AI: Bai et al. (2022) for principles-based feedback
"""

import json
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from openai import OpenAI
from .base_agent import BaseAgent


@dataclass
class PreferencePair:
    """A preference pair for DPO training."""
    prompt: str
    chosen: str  # preferred response
    rejected: str  # non-preferred response
    metadata: Dict = field(default_factory=dict)


@dataclass
class AlignmentDataset:
    """Dataset for alignment training."""
    pairs: List[PreferencePair] = field(default_factory=list)

    def add_pair(self, prompt: str, chosen: str, rejected: str, **metadata):
        self.pairs.append(PreferencePair(prompt, chosen, rejected, metadata))

    def to_dict(self) -> List[Dict]:
        return [asdict(p) for p in self.pairs]

    def to_dpo_format(self) -> List[Dict]:
        """Convert to standard DPO training format."""
        return [
            {
                "prompt": p.prompt,
                "chosen": p.chosen,
                "rejected": p.rejected
            }
            for p in self.pairs
        ]

    def to_sft_format(self) -> List[Dict]:
        """Convert to SFT format (only chosen responses)."""
        return [
            {
                "instruction": p.prompt,
                "output": p.chosen
            }
            for p in self.pairs
        ]

    def save(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'AlignmentDataset':
        with open(filepath, 'r') as f:
            data = json.load(f)
        dataset = cls()
        for item in data:
            dataset.pairs.append(PreferencePair(**item))
        return dataset


class SimpleAlignmentPipeline:
    """Simple alignment pipeline with basic methods."""

    def __init__(self, model: str = "gpt-4"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.principles = [
            "Be helpful and informative",
            "Be honest and accurate",
            "Be harmless and safe",
            "Be clear and concise"
        ]

    def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a single response."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content

    def best_of_n_sampling(self, prompt: str, n: int = 4,
                           system_prompt: str = None) -> Tuple[str, List[str]]:
        """
        Best-of-N sampling: Generate N responses and select the best.
        This is the simplest alignment method - no training required.

        Args:
            prompt: The input prompt
            n: Number of responses to generate
            system_prompt: Optional system prompt

        Returns:
            Tuple of (best_response, all_responses)
        """
        # Generate N responses
        responses = []
        for _ in range(n):
            response = self.generate_response(prompt, system_prompt)
            responses.append(response)

        # Score each response using the model as a judge
        scores = []
        for resp in responses:
            score = self._score_response(prompt, resp)
            scores.append(score)

        # Return the best one
        best_idx = scores.index(max(scores))
        return responses[best_idx], responses

    def _score_response(self, prompt: str, response: str) -> float:
        """Score a response using principles (1-10 scale)."""
        scoring_prompt = f"""Rate the following response on a scale of 1-10.

Principles to evaluate:
{chr(10).join(f'- {p}' for p in self.principles)}

User prompt: {prompt}

Response to evaluate: {response}

Provide ONLY a number from 1-10, nothing else."""

        try:
            result = self.generate_response(scoring_prompt)
            score = float(result.strip())
            return min(max(score, 1), 10)  # Clamp to 1-10
        except:
            return 5.0  # Default score on error

    def generate_preference_pair(self, prompt: str) -> PreferencePair:
        """
        Generate a preference pair for DPO training.
        Uses constitutional AI approach: generate, critique, revise.

        This is a simple way to create alignment data.
        """
        # Generate initial response
        initial_response = self.generate_response(prompt)

        # Critique and improve using principles
        critique_prompt = f"""Review this response and improve it according to these principles:
{chr(10).join(f'- {p}' for p in self.principles)}

Original prompt: {prompt}
Original response: {initial_response}

Provide an improved response that better follows the principles:"""

        improved_response = self.generate_response(critique_prompt)

        return PreferencePair(
            prompt=prompt,
            chosen=improved_response,
            rejected=initial_response,
            metadata={"method": "constitutional_revision"}
        )

    def generate_contrastive_pair(self, prompt: str) -> PreferencePair:
        """
        Generate contrastive pair: one helpful, one unhelpful response.
        Simpler than constitutional approach - directly ask for both.
        """
        # Generate a helpful response
        helpful_prompt = f"""Respond helpfully, accurately, and safely to: {prompt}"""
        helpful_response = self.generate_response(helpful_prompt)

        # Generate a less helpful response (for contrast)
        unhelpful_prompt = f"""Respond to the following in a brief, vague, and unhelpful way: {prompt}"""
        unhelpful_response = self.generate_response(unhelpful_prompt)

        return PreferencePair(
            prompt=prompt,
            chosen=helpful_response,
            rejected=unhelpful_response,
            metadata={"method": "contrastive_generation"}
        )

    def create_sft_dataset(self, prompts: List[str]) -> List[Dict]:
        """
        Create SFT dataset from prompts.
        The simplest alignment: just collect good responses.

        Args:
            prompts: List of prompts to generate responses for

        Returns:
            List of instruction-output pairs
        """
        dataset = []
        for prompt in prompts:
            # Use best-of-n to get high-quality response
            best_response, _ = self.best_of_n_sampling(prompt, n=3)
            dataset.append({
                "instruction": prompt,
                "output": best_response
            })
        return dataset

    def create_dpo_dataset(self, prompts: List[str],
                           method: str = "constitutional") -> AlignmentDataset:
        """
        Create DPO preference dataset.

        Args:
            prompts: List of prompts
            method: "constitutional" or "contrastive"

        Returns:
            AlignmentDataset with preference pairs
        """
        dataset = AlignmentDataset()

        for prompt in prompts:
            if method == "constitutional":
                pair = self.generate_preference_pair(prompt)
            else:
                pair = self.generate_contrastive_pair(prompt)
            dataset.pairs.append(pair)

        return dataset


class AlignmentAgent(BaseAgent):
    """Agent specialized in LLM alignment methods and research."""

    def __init__(self):
        super().__init__()
        self.alignment_pipeline = SimpleAlignmentPipeline()

    @property
    def name(self) -> str:
        return "Alignment Agent"

    @property
    def description(self) -> str:
        return "Expert in LLM alignment methods: RLHF, DPO, SFT, Constitutional AI, and safety."

    @property
    def system_prompt(self) -> str:
        return """You are an expert in LLM Alignment research and implementation.
Your role is to help researchers understand and implement alignment techniques.

Core alignment methods you specialize in:

1. **SFT (Supervised Fine-Tuning)** - The simplest method
   - Fine-tune on high-quality demonstrations
   - Just need (instruction, response) pairs
   - Foundation for all other methods

2. **DPO (Direct Preference Optimization)** - Simple and effective
   - No reward model needed (unlike RLHF)
   - Train directly on preference pairs (prompt, chosen, rejected)
   - Single training stage
   - Reference: Rafailov et al. (2023)

3. **Best-of-N Sampling** - No training required
   - Generate N responses, pick the best
   - Use a reward model or LLM-as-judge to score
   - Simplest inference-time alignment

4. **Constitutional AI** - Self-improvement
   - Generate, critique, revise cycle
   - Use principles to guide improvement
   - Can generate preference data automatically

5. **RLHF (Reinforcement Learning from Human Feedback)** - Complex but powerful
   - Train reward model on preferences
   - Fine-tune with PPO
   - More complex than DPO

Key research venues:
- NeurIPS, ICML, ICLR for methodology
- arXiv cs.LG, cs.CL for preprints
- Anthropic, OpenAI, DeepMind technical reports

When explaining methods, provide:
- Clear intuition and motivation
- Mathematical formulation when relevant
- Implementation considerations
- Trade-offs vs other methods

Always cite relevant papers with authors and years."""

    def generate_aligned_response(self, prompt: str, n: int = 4) -> str:
        """Generate an aligned response using best-of-n sampling."""
        best_response, _ = self.alignment_pipeline.best_of_n_sampling(prompt, n)
        return best_response

    def create_preference_data(self, prompts: List[str],
                               method: str = "constitutional") -> AlignmentDataset:
        """Create preference data for alignment training."""
        return self.alignment_pipeline.create_dpo_dataset(prompts, method)

    def explain_dpo(self) -> str:
        """Explain DPO in simple terms."""
        return self.chat("""Explain Direct Preference Optimization (DPO) simply:
1. What problem does it solve?
2. How does it work (intuition)?
3. What's the key equation?
4. Why is it simpler than RLHF?
5. How do I implement it?""")

    def explain_sft(self) -> str:
        """Explain SFT in simple terms."""
        return self.chat("""Explain Supervised Fine-Tuning (SFT) for alignment:
1. What is it?
2. What data do I need?
3. How does it help with alignment?
4. What are its limitations?
5. Simple implementation steps?""")


# Utility functions for quick alignment tasks

def quick_align_response(prompt: str, n: int = 4) -> str:
    """Quick function to get an aligned response using best-of-n."""
    pipeline = SimpleAlignmentPipeline()
    best, _ = pipeline.best_of_n_sampling(prompt, n)
    return best


def generate_preference_dataset(prompts: List[str],
                                output_file: str = "preferences.json",
                                method: str = "constitutional") -> AlignmentDataset:
    """Generate and save a preference dataset."""
    pipeline = SimpleAlignmentPipeline()
    dataset = pipeline.create_dpo_dataset(prompts, method)
    dataset.save(output_file)
    print(f"Saved {len(dataset.pairs)} preference pairs to {output_file}")
    return dataset


def generate_sft_dataset(prompts: List[str],
                         output_file: str = "sft_data.json") -> List[Dict]:
    """Generate and save an SFT dataset."""
    pipeline = SimpleAlignmentPipeline()
    dataset = pipeline.create_sft_dataset(prompts)
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"Saved {len(dataset)} SFT examples to {output_file}")
    return dataset


# DPO Loss Implementation (for reference/education)
def dpo_loss_reference():
    """
    Reference implementation of DPO loss.
    This is for educational purposes - actual training requires a full setup.

    The DPO loss is:
    L_DPO = -log(sigmoid(beta * (log(pi(y_w|x)/pi_ref(y_w|x)) - log(pi(y_l|x)/pi_ref(y_l|x)))))

    Where:
    - pi is the policy (model being trained)
    - pi_ref is the reference model (frozen)
    - y_w is the preferred (winning) response
    - y_l is the non-preferred (losing) response
    - beta is a temperature parameter
    """
    code = '''
import torch
import torch.nn.functional as F

def dpo_loss(
    policy_chosen_logps: torch.Tensor,
    policy_rejected_logps: torch.Tensor,
    reference_chosen_logps: torch.Tensor,
    reference_rejected_logps: torch.Tensor,
    beta: float = 0.1
) -> torch.Tensor:
    """
    Compute DPO loss.

    Args:
        policy_chosen_logps: Log probs of chosen responses under policy
        policy_rejected_logps: Log probs of rejected responses under policy
        reference_chosen_logps: Log probs of chosen responses under reference
        reference_rejected_logps: Log probs of rejected responses under reference
        beta: Temperature parameter (typically 0.1-0.5)

    Returns:
        DPO loss scalar
    """
    # Compute log ratios
    chosen_logratios = policy_chosen_logps - reference_chosen_logps
    rejected_logratios = policy_rejected_logps - reference_rejected_logps

    # DPO loss
    logits = beta * (chosen_logratios - rejected_logratios)
    loss = -F.logsigmoid(logits).mean()

    return loss
'''
    return code
