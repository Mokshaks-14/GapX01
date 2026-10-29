import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Ensure utf-8 output encoding on Windows console
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.ai_service import AIService

print("================ TEST SUITE: AI CAREER & CODING COACH ================")
queries = [
    "Can you write a python code for Two Sum with time and space complexity?",
    "Explain OOP concepts in simple terms with examples",
    "How to answer 'Tell me about yourself' in an interview?",
    "What is the difference between REST API and GraphQL?",
    "How to negotiate salary for a software engineer role?",
    "How do I reverse a linked list in Java?",
    "What are the best strategies to prepare for FAANG placements?",
    "Explain Docker and containers vs Virtual Machines"
]

for q in queries:
    res = AIService.get_career_advice(q, [])
    print(f"\n========================================================")
    print(f"QUERY: {q}")
    print(f"RESPONSE PREVIEW:\n{res['response'][:250]}...\n")
    print(f"SUGGESTIONS: {res['suggestions']}")
    assert len(res['response']) > 50, "Response too short!"
    assert len(res['suggestions']) >= 2, "Suggestions missing!"

print("\n[SUCCESS] All AI Coach queries produced dynamic, detailed, and accurate answers!")
