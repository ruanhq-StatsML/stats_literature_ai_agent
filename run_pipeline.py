#!/usr/bin/env python3
"""Run full pipeline: Psychiatry → Applications → Product Manager"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents import PsychiatryAgent, ApplicationsAgent, ProductManagerAgent

# Initialize all three agents
psychiatry = PsychiatryAgent()
applications = ApplicationsAgent()
pm = ProductManagerAgent()

query = '''How can psychiatry research on decision-making, impulse control, cognitive load, attention, and reward systems be translated into practical e-commerce platform features?'''

print('=' * 70)
print('FULL PIPELINE: Psychiatry → Applications → Product Manager')
print('=' * 70)

# Step 1: Psychiatry Agent - Clinical/Research Foundation
print()
print('>>> STEP 1: PSYCHIATRY AGENT (Clinical Research Foundation)')
print('-' * 70)
psych_response = psychiatry.chat(query)
print(psych_response)

# Step 2: Applications Agent - Real-world implementations
print()
print('>>> STEP 2: APPLICATIONS AGENT (Industry Use Cases)')
print('-' * 70)
apps_response = applications.chat(f'''Based on these psychiatry research insights:
{psych_response[:2000]}

How are these principles currently applied in real e-commerce platforms?
What are successful case studies and implementations?''')
print(apps_response)

# Step 3: Product Manager Agent - Product Strategy
print()
print('>>> STEP 3: PRODUCT MANAGER AGENT (Product Strategy)')
print('-' * 70)
pm_response = pm.chat(f'''Based on the psychiatry research and industry applications:

PSYCHIATRY INSIGHTS:
{psych_response[:1500]}

INDUSTRY APPLICATIONS:
{apps_response[:1500]}

Now synthesize this into actionable product recommendations:
1. Define specific user personas
2. Prioritize 3-5 MVP features
3. Define success metrics for each
4. Outline implementation phases
5. Address ethical considerations''')
print(pm_response)

print()
print('=' * 70)
print('PIPELINE COMPLETE')
print('=' * 70)
