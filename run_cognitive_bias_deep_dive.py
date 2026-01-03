#!/usr/bin/env python3
"""Deep Dive: Quantitative Analysis of Cognitive Biases in Purchasing Behavior"""

import os
from dotenv import load_dotenv
load_dotenv()

from agents import PsychologyAgent, StatisticsAgent, ProductManagerAgent

psychology = PsychologyAgent()
stats = StatisticsAgent()
pm = ProductManagerAgent()

print('=' * 70)
print('DEEP DIVE: Cognitive/Behavioral Biases in Purchasing Intentions')
print('=' * 70)

# Step 1: Psychology Agent - Quantitative Research on Biases
print()
print('>>> STEP 1: PSYCHOLOGY AGENT (Quantitative Bias Research)')
print('-' * 70)
psych_query = '''Provide a QUANTITATIVE deep dive on cognitive and behavioral biases affecting online purchasing intentions. For each bias, include:

1. **ANCHORING BIAS**
   - Effect sizes from empirical studies (Cohen's d, percentage changes)
   - Key experiments (Tversky & Kahneman, Ariely)
   - Quantified impact on willingness-to-pay
   - Moderating variables (expertise, time pressure)

2. **LOSS AVERSION**
   - Loss aversion coefficient (typical λ = 2.0-2.5)
   - Framing effects on conversion rates
   - Quantified impact of "limited time" vs "save money" framing
   - Endowment effect measurements

3. **SOCIAL PROOF / CONFORMITY**
   - Effect of review quantity on conversion (studies with N and effect sizes)
   - Star rating impact (quantified conversion lift per star)
   - "X people bought this" effectiveness metrics
   - Bandwagon effect measurements

4. **SCARCITY EFFECT**
   - Commodity theory empirical findings
   - "Only X left" effect on purchase speed and conversion
   - Time-limited offer effectiveness (countdown timers)
   - Reactance effects and backfire rates

5. **CHOICE OVERLOAD (Paradox of Choice)**
   - Iyengar & Lepper jam study findings
   - Optimal number of choices research
   - Decision fatigue quantification
   - Satisficing vs. maximizing behavior metrics

6. **DECOY EFFECT (Asymmetric Dominance)**
   - Effect sizes on choice share shifts
   - Huber, Payne & Puto original findings
   - E-commerce pricing strategy applications

7. **DEFAULT EFFECT / STATUS QUO BIAS**
   - Opt-in vs opt-out conversion differences
   - Default option selection rates
   - 401k and organ donation parallels to e-commerce

8. **PRESENT BIAS / HYPERBOLIC DISCOUNTING**
   - Discount rates in consumer behavior
   - "Buy now" vs "Buy later" conversion differences
   - Impulse purchase metrics

For each bias, provide:
- Original research citations with sample sizes
- Effect sizes (Cohen's d, odds ratios, percentage lifts)
- Confidence intervals where available
- Replication status and meta-analysis findings'''

psych_response = psychology.chat(psych_query)
print(psych_response)

# Step 2: Statistics Agent - Measurement Methodologies
print()
print('>>> STEP 2: STATISTICS AGENT (Measurement & Analysis Methods)')
print('-' * 70)
stats_query = f'''Based on the cognitive bias research:
{psych_response[:3000]}

Provide QUANTITATIVE methodologies for measuring these biases in e-commerce:

1. **EXPERIMENTAL DESIGN FOR BIAS MEASUREMENT**
   - Within-subject vs between-subject designs
   - Sample size calculations for detecting bias effects
   - Power analysis for typical effect sizes (d = 0.2 to 0.8)
   - Multi-armed bandit approaches for real-time optimization

2. **STATISTICAL MODELS**
   - Logistic regression for conversion modeling
   - Mixed-effects models for repeated measures
   - Structural equation modeling for bias pathways
   - Bayesian approaches for belief updating

3. **EFFECT SIZE INTERPRETATION**
   - Cohen's d benchmarks for e-commerce
   - Practical significance vs statistical significance
   - Minimum detectable effects for business impact
   - Confidence interval interpretation

4. **BIAS-SPECIFIC METRICS**
   - Anchoring: Willingness-to-pay deviation from reference
   - Loss aversion: λ coefficient estimation methods
   - Social proof: Review elasticity of conversion
   - Scarcity: Purchase velocity metrics
   - Choice overload: Decision time and abandonment rates

5. **CAUSAL INFERENCE CONSIDERATIONS**
   - Controlling for confounds in bias studies
   - Propensity score matching for observational data
   - Instrumental variables for price anchoring
   - Regression discontinuity for threshold effects

6. **META-ANALYTIC SYNTHESIS**
   - Heterogeneity assessment (I², Q statistic)
   - Publication bias detection (funnel plots, Egger's test)
   - Random-effects vs fixed-effects models
   - Moderator analysis for context effects'''

stats_response = stats.chat(stats_query)
print(stats_response)

# Step 3: Product Manager - Quantified Feature Impact
print()
print('>>> STEP 3: PRODUCT MANAGER (Quantified Feature Recommendations)')
print('-' * 70)
pm_query = f'''Based on the quantitative bias research and statistical methodologies:

PSYCHOLOGY RESEARCH:
{psych_response[:2500]}

STATISTICAL METHODS:
{stats_response[:2000]}

Create a QUANTIFIED feature recommendation framework:

1. **BIAS-TO-FEATURE MAPPING WITH EXPECTED LIFTS**
   - For each cognitive bias, specify:
     - Feature implementation
     - Expected effect size (based on research)
     - 95% confidence interval for conversion lift
     - Sample size needed to detect effect

2. **PRIORITIZATION MATRIX**
   - Rank features by: Expected Lift × Feasibility × Confidence
   - Include uncertainty quantification
   - Risk-adjusted ROI estimates

3. **A/B TEST DESIGN FOR EACH BIAS**
   - Primary metric and minimum detectable effect
   - Required sample size and test duration
   - Stratification variables
   - Early stopping boundaries

4. **INTERACTION EFFECTS**
   - Which biases amplify each other?
   - Which biases conflict?
   - Optimal combination strategies

5. **USER SEGMENT SUSCEPTIBILITY**
   - Which user segments are most susceptible to each bias?
   - Quantified response heterogeneity
   - Personalization opportunities

6. **ETHICAL BOUNDARIES**
   - At what effect size does a nudge become manipulation?
   - Thresholds for acceptable influence
   - Transparency requirements'''

pm_response = pm.chat(pm_query)
print(pm_response)

print()
print('=' * 70)
print('COGNITIVE BIAS DEEP DIVE COMPLETE')
print('=' * 70)

# Save outputs
with open('docs/cognitive_bias_deep_dive.txt', 'w') as f:
    f.write("COGNITIVE BIAS QUANTITATIVE DEEP DIVE\n")
    f.write("=" * 60 + "\n\n")
    f.write("PSYCHOLOGY AGENT - Quantitative Bias Research:\n")
    f.write("-" * 50 + "\n")
    f.write(psych_response + "\n\n")
    f.write("STATISTICS AGENT - Measurement Methodologies:\n")
    f.write("-" * 50 + "\n")
    f.write(stats_response + "\n\n")
    f.write("PRODUCT MANAGER - Quantified Recommendations:\n")
    f.write("-" * 50 + "\n")
    f.write(pm_response + "\n")

print("\n✓ Output saved to: docs/cognitive_bias_deep_dive.txt")
