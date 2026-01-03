#!/usr/bin/env python3
"""Run full pipeline: Psychology Research → E-commerce Applications"""

import os
from dotenv import load_dotenv
load_dotenv()

from agents import PsychologyAgent, ApplicationsAgent, ProductManagerAgent, StatisticsAgent

# Initialize agents
psychology = PsychologyAgent()
applications = ApplicationsAgent()
pm = ProductManagerAgent()
stats = StatisticsAgent()

print('=' * 70)
print('FULL PIPELINE: Psychology Methodologies → E-commerce Applications')
print('=' * 70)

# Step 1: Psychology Agent - Research Foundation
print()
print('>>> STEP 1: PSYCHOLOGY AGENT (Research Methodologies)')
print('-' * 70)
psych_query = '''Explore key psychological research methodologies and theories that can be applied to e-commerce platforms:

1. **Behavioral Psychology Methods**
   - Classical and operant conditioning in user behavior
   - Habit formation research (e.g., Fogg Behavior Model)
   - Behavioral nudges and choice architecture

2. **Cognitive Psychology Frameworks**
   - Attention and perception studies
   - Memory and recall in product discovery
   - Mental models and information processing

3. **Social Psychology Principles**
   - Social proof and conformity (Cialdini)
   - Reciprocity and commitment
   - Scarcity and urgency effects

4. **Consumer Psychology Research**
   - Price perception and anchoring
   - Brand trust and loyalty formation
   - Emotional vs. rational decision-making

5. **User Experience Psychology**
   - Flow state in shopping experiences
   - Aesthetic-usability effect
   - Peak-end rule in customer journey

For each area, provide:
- Key researchers and seminal papers
- Core methodologies used
- Potential e-commerce applications'''

psych_response = psychology.chat(psych_query)
print(psych_response)

# Step 2: Applications Agent - Real-world implementations
print()
print('>>> STEP 2: APPLICATIONS AGENT (Industry Use Cases)')
print('-' * 70)
apps_query = f'''Based on these psychology research insights:
{psych_response[:3000]}

How are these psychological methodologies currently applied in real e-commerce platforms?

Provide:
1. Specific company examples (Amazon, Netflix, Booking.com, etc.)
2. Feature implementations based on psychology research
3. Measured outcomes and success metrics
4. Case studies of psychology-driven A/B tests'''

apps_response = applications.chat(apps_query)
print(apps_response)

# Step 3: Product Manager Agent - Product Strategy
print()
print('>>> STEP 3: PRODUCT MANAGER AGENT (Product Strategy)')
print('-' * 70)
pm_query = f'''Based on the psychology research and industry applications:

PSYCHOLOGY RESEARCH:
{psych_response[:2000]}

INDUSTRY APPLICATIONS:
{apps_response[:2000]}

Create a comprehensive product strategy for implementing psychology-based features in an e-commerce platform:

1. **Problem Statement** - What user problems do these methodologies solve?

2. **User Personas** - Define 3-4 personas based on psychological profiles

3. **Feature Prioritization** - Rank 5-7 features by impact and feasibility:
   - Feature name
   - Psychology principle applied
   - Expected user behavior change
   - Success metrics

4. **MVP Definition** - Which 3 features should be in MVP?

5. **Ethical Framework** - Guidelines for responsible implementation

6. **Go-to-Market Considerations** - How to position psychology-driven features'''

pm_response = pm.chat(pm_query)
print(pm_response)

# Step 4: Statistics Agent - A/B Testing Framework
print()
print('>>> STEP 4: STATISTICS AGENT (Experimentation Framework)')
print('-' * 70)
stats_query = f'''Design an A/B testing framework for psychology-based e-commerce features:

FEATURES TO TEST:
{pm_response[:1500]}

Provide:
1. **Experiment Design** for each feature type:
   - Sample size requirements
   - Randomization considerations
   - Duration based on psychological adaptation

2. **Metrics Framework**:
   - Behavioral metrics (clicks, time, navigation)
   - Psychological metrics (trust scores, satisfaction)
   - Business metrics (conversion, AOV, retention)

3. **Early Stopping Considerations**:
   - When psychological effects might take longer to manifest
   - Novelty vs. habituation timelines
   - Seasonal and contextual factors

4. **Segmentation Strategy**:
   - By psychological profile
   - By customer lifecycle stage
   - By product category'''

stats_response = stats.chat(stats_query)
print(stats_response)

print()
print('=' * 70)
print('PSYCHOLOGY → E-COMMERCE PIPELINE COMPLETE')
print('=' * 70)

# Save responses for document generation
with open('docs/psychology_pipeline_output.txt', 'w') as f:
    f.write("PSYCHOLOGY AGENT OUTPUT:\n")
    f.write("=" * 50 + "\n")
    f.write(psych_response + "\n\n")
    f.write("APPLICATIONS AGENT OUTPUT:\n")
    f.write("=" * 50 + "\n")
    f.write(apps_response + "\n\n")
    f.write("PRODUCT MANAGER AGENT OUTPUT:\n")
    f.write("=" * 50 + "\n")
    f.write(pm_response + "\n\n")
    f.write("STATISTICS AGENT OUTPUT:\n")
    f.write("=" * 50 + "\n")
    f.write(stats_response + "\n")

print("\n✓ Pipeline output saved to: docs/psychology_pipeline_output.txt")
