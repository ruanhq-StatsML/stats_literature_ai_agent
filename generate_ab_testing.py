#!/usr/bin/env python3
"""Generate A/B Testing Methodology with Statistics + Psychology Agents"""

import os
from dotenv import load_dotenv
load_dotenv()

from agents import StatisticsAgent, PsychologyAgent, ProductManagerAgent

stats = StatisticsAgent()
psych = PsychologyAgent()
pm = ProductManagerAgent()

context = '''We are implementing an "Optimized Checkout" feature for an e-commerce platform with these KPIs:
- Cart abandonment rate: 70% → 50% (target -20%)
- Checkout completion time: 4.5 min → 1.5 min
- Conversion rate: +10%
- Customer satisfaction (CSAT): 6.5 → 8+/10

The feature includes: one-page checkout, auto-fill forms, real-time validation, dynamic cart edits, express checkout options.

Rollout plan: Alpha (internal) → Beta (5%) → Limited (25%) → Expanded (50%) → GA (100%)'''

print('=' * 70)
print('A/B TESTING METHODOLOGY: Statistics + Psychology Collaboration')
print('=' * 70)

# Step 1: Statistics Agent - A/B Testing Framework
print()
print('>>> STEP 1: STATISTICS AGENT (A/B Testing Framework)')
print('-' * 70)
stats_query = f'''{context}

Design a comprehensive A/B testing methodology for this checkout optimization, including:

1. **Experiment Design**
   - Sample size calculation (with assumptions)
   - Randomization strategy
   - Control vs treatment allocation
   - Stratification considerations

2. **Primary & Secondary Metrics**
   - Which metrics to use as primary (and why)
   - Guardrail metrics to monitor
   - How to handle multiple comparisons

3. **Early Stopping Strategy**
   - Sequential testing approach (e.g., group sequential, always-valid p-values)
   - Spending functions (O'Brien-Fleming, Pocock, etc.)
   - When to stop for futility vs efficacy
   - Bayesian vs Frequentist considerations
   - Practical stopping rules

4. **Statistical Methods**
   - Hypothesis testing approach
   - Confidence intervals
   - Effect size estimation
   - How to handle ratio metrics (conversion rate)

5. **Common Pitfalls to Avoid**
   - Peeking problem
   - Simpson's paradox
   - Novelty/primacy effects

Provide specific formulas and practical guidance.'''

stats_response = stats.chat(stats_query)
print(stats_response)

# Step 2: Psychology Agent - Behavioral Considerations
print()
print('>>> STEP 2: PSYCHOLOGY AGENT (Behavioral & Cognitive Factors)')
print('-' * 70)
psych_query = f'''{context}

Previous statistics guidance:
{stats_response[:2000]}

From a cognitive and behavioral psychology perspective, help enhance the A/B testing methodology:

1. **Novelty & Habituation Effects**
   - How long do novelty effects typically last?
   - How to account for habituation in experiment duration
   - Learning curve considerations for new UI

2. **Cognitive Biases in User Behavior**
   - Which biases might affect checkout behavior?
   - How might these biases differ between control and treatment?
   - Anchoring, loss aversion, choice overload effects

3. **Segmentation by Psychological Profiles**
   - Should we segment users by decision-making styles?
   - Impulsive vs deliberate shoppers
   - Risk-averse vs risk-seeking users

4. **Temporal & Contextual Factors**
   - Time-of-day effects on decision-making
   - Day-of-week patterns
   - Seasonal/promotional period considerations

5. **Survey & Qualitative Metrics**
   - What psychological constructs to measure (cognitive load, trust, anxiety)?
   - Validated scales to use (NASA-TLX, SUS, etc.)
   - When to deploy surveys without biasing results

6. **Ethical Considerations**
   - Avoiding dark patterns
   - Informed consent in experimentation
   - Vulnerable population considerations'''

psych_response = psych.chat(psych_query)
print(psych_response)

# Step 3: Synthesis - Combined Methodology
print()
print('>>> STEP 3: PRODUCT MANAGER (Synthesized A/B Testing Plan)')
print('-' * 70)
pm_query = f'''Synthesize these expert inputs into a unified A/B Testing Plan document:

STATISTICS AGENT INPUT:
{stats_response[:2500]}

PSYCHOLOGY AGENT INPUT:
{psych_response[:2500]}

Create an actionable A/B Testing Plan that includes:

1. **Executive Summary** - Key decisions and rationale

2. **Experiment Configuration**
   - Sample size and duration
   - Traffic allocation strategy
   - Randomization unit

3. **Metrics Framework**
   - Primary metric with success threshold
   - Secondary metrics
   - Guardrail metrics

4. **Early Stopping Protocol**
   - Decision rules with specific thresholds
   - Interim analysis schedule
   - Stopping boundaries

5. **Segmentation Strategy**
   - Key segments to analyze
   - Psychological profile considerations

6. **Timeline & Milestones**
   - Burn-in period (for novelty effects)
   - Minimum runtime
   - Decision checkpoints

7. **Risk Mitigation**
   - Statistical pitfalls addressed
   - Psychological biases accounted for
   - Rollback criteria

Make it practical and ready for implementation.'''

pm_response = pm.chat(pm_query)
print(pm_response)

print()
print('=' * 70)
print('A/B TESTING METHODOLOGY COMPLETE')
print('=' * 70)
