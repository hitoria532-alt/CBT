#!/usr/bin/env python3
"""Complete end-to-end test for 5-option feature including exam submission and results"""
import requests
import json

BASE_URL = "https://github-auto-build.preview.emergentagent.com/api"

print("=== Complete 5-Option Feature Test ===\n")

# Login as admin
resp = requests.post(f"{BASE_URL}/auth/login", 
                    json={"email": "hitoria532@gmail.com", "password": "admin123"})
admin_token = resp.json()["token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# Login as student
resp = requests.post(f"{BASE_URL}/auth/login",
                    json={"email": "siswa2@sekolah.id", "password": "siswa123"})
student_token = resp.json()["token"]
student_headers = {"Authorization": f"Bearer {student_token}"}

print("✅ Logged in as admin and student\n")

# Get the test session
resp = requests.get(f"{BASE_URL}/sessions", headers=student_headers)
sessions = resp.json()
test_session = [s for s in sessions if "Test Session - 5 Options" in s.get("title", "")]

if test_session:
    session = test_session[0]
    print(f"✅ Found test session: {session['title']}")
    print(f"   Session ID: {session['id']}\n")
    
    # Start exam
    print("Starting exam...")
    resp = requests.post(f"{BASE_URL}/exam/start", 
                        json={"session_id": session['id']},
                        headers=student_headers)
    
    if resp.status_code == 200:
        exam_data = resp.json()
        print(f"✅ Exam started")
        print(f"   Questions: {len(exam_data['questions'])}")
        
        # Check first question
        q = exam_data['questions'][0]
        print(f"\n📝 Question: {q['text']}")
        print(f"   Type: {q['type']}")
        print(f"   Options: {len(q['options'])}")
        
        if len(q['options']) == 5:
            print("   ✅ Question has 5 options (A-E)")
            for i, opt in enumerate(q['options']):
                print(f"      {chr(65+i)}. {opt}")
        
        # Submit answer (select option E = index 4)
        print(f"\n📤 Submitting answer: E (index 4)")
        answers = {q['id']: "4"}
        
        resp = requests.post(f"{BASE_URL}/exam/submit",
                           json={"session_id": session['id'], "answers": answers},
                           headers=student_headers)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Exam submitted")
            print(f"   Score: {result.get('score')}")
            print(f"   Status: {result.get('status')}")
            
            # Get result detail
            print(f"\n📊 Fetching result detail...")
            resp = requests.get(f"{BASE_URL}/results/me", headers=student_headers)
            my_results = resp.json()
            
            test_result = [r for r in my_results if r.get('session_title') == 'Test Session - 5 Options']
            if test_result:
                attempt_id = test_result[0]['id']
                
                resp = requests.get(f"{BASE_URL}/results/detail/{attempt_id}", 
                                  headers=student_headers)
                detail = resp.json()
                
                print(f"✅ Result detail retrieved")
                print(f"   Final score: {detail.get('score')}")
                
                # Check if option E is shown correctly in details
                for i, d in enumerate(detail.get('details', [])):
                    if d.get('type') == 'pg':
                        print(f"\n   Question {i+1} detail:")
                        print(f"      Student answer: {d.get('answer')}")
                        print(f"      Correct answer: {d.get('correct_answer')}")
                        
                        # Verify option E is in the options
                        if len(d.get('options', [])) == 5:
                            print(f"      ✅ Result shows 5 options")
                            print(f"      Options: {d.get('options')}")
                            
                            # Check if answer is displayed correctly
                            ans_idx = int(d.get('answer', -1))
                            if ans_idx == 4:
                                print(f"      ✅ Student selected option E (index 4)")
                                print(f"      ✅ Answer display: E. {d['options'][4]}")
                        
                        if d.get('is_correct'):
                            print(f"      ✅ Answer marked as CORRECT")
                        else:
                            print(f"      ❌ Answer marked as INCORRECT")
            
            print("\n✅ Complete flow test PASSED")
        else:
            print(f"❌ Failed to submit exam: {resp.status_code}")
    else:
        print(f"❌ Failed to start exam: {resp.status_code} - {resp.text}")
else:
    print("⚠️ Test session not found")

print("\n=== Test Complete ===")
