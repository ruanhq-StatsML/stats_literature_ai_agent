#!/usr/bin/env python3
"""Generate PRD for Optimized Checkout feature"""

import os
from dotenv import load_dotenv
load_dotenv()

from agents import ProductManagerAgent

pm = ProductManagerAgent()

query = '''Create a detailed Product Requirements Document (PRD) for an "Optimized Checkout" feature for an e-commerce platform.

Context: This feature is informed by psychiatry research on:
- Decision-making & impulse control (Bechara, 2005) - humans prefer immediate gratification
- Cognitive load theory (Sweller, 1988) - working memory overload decreases satisfaction
- Attention research - colors, movement, relevance direct focus

Target personas:
1. Casual Shopper - bounces between platforms, makes impulse purchases
2. Streamlined Shopper - values speed & simplicity

The PRD should include:
1. Executive Summary
2. Problem Statement & User Pain Points
3. Goals & Success Metrics (with specific KPIs)
4. User Stories & Use Cases
5. Functional Requirements (detailed feature specs)
6. Non-Functional Requirements (performance, security, accessibility)
7. UX/UI Guidelines (based on cognitive load & attention research)
8. Technical Considerations
9. Dependencies & Integrations
10. Risks & Mitigations
11. Out of Scope
12. Release Criteria & Rollout Plan

Make it comprehensive and actionable for an engineering team.'''

print('=' * 70)
print('PRODUCT REQUIREMENTS DOCUMENT: Optimized Checkout')
print('=' * 70)
print()
response = pm.chat(query)
print(response)
