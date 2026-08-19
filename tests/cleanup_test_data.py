#!/usr/bin/env python3
"""Clean up test data created during testing"""
import requests

BASE_URL = "https://github-auto-build.preview.emergentagent.com/api"

# Login as admin
resp = requests.post(f"{BASE_URL}/auth/login", 
                    json={"email": "hitoria532@gmail.com", "password": "admin123"})
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

print("Cleaning up test data...\n")

# Delete test session
resp = requests.get(f"{BASE_URL}/sessions", headers=headers)
sessions = resp.json()
test_sessions = [s for s in sessions if "Test Session - 5 Options" in s.get("title", "")]
for s in test_sessions:
    resp = requests.delete(f"{BASE_URL}/sessions/{s['id']}", headers=headers)
    print(f"✅ Deleted test session: {s['id']}")

# Delete test package
resp = requests.get(f"{BASE_URL}/packages", headers=headers)
packages = resp.json()
test_packages = [p for p in packages if "Test Package - 5 Options" in p.get("title", "")]
for p in test_packages:
    resp = requests.delete(f"{BASE_URL}/packages/{p['id']}", headers=headers)
    print(f"✅ Deleted test package: {p['id']}")

# Delete test questions
resp = requests.get(f"{BASE_URL}/questions", headers=headers)
questions = resp.json()
test_questions = [q for q in questions if any(x in q.get("text", "") for x in [
    "Test question with 5 options",
    "Test question with 4 options",
    "Invalid question",
    "Import test"
])]
for q in test_questions:
    resp = requests.delete(f"{BASE_URL}/questions/{q['id']}", headers=headers)
    print(f"✅ Deleted test question: {q['id']}")

# Delete test categories
resp = requests.get(f"{BASE_URL}/categories", headers=headers)
categories = resp.json()
test_cats = [c for c in categories if any(x in c.get("name", "") for x in [
    "Test5Opt", "Test4Opt", "TestInvalid"
])]
for c in test_cats:
    resp = requests.delete(f"{BASE_URL}/categories/{c['id']}", headers=headers)
    print(f"✅ Deleted test category: {c['id']}")

print(f"\n✅ Cleanup complete")
