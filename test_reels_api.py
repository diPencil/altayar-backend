"""
Test reels API endpoint
"""
import requests
import json

# Test the reels endpoint
url = "http://localhost:8082/api/reels?limit=10"

try:
    print("Testing GET /api/reels...")
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal Reels Returned: {len(data)}")
        
        for i, reel in enumerate(data, 1):
            print(f"\nReel #{i}")
            print(f"  ID: {reel.get('id')}")
            print(f"  Title: {reel.get('title')}")
            print(f"  Status: {reel.get('status')}")
            print(f"  Video Type: {reel.get('video_type')}")
            print(f"  Video URL: {reel.get('video_url')[:60] if reel.get('video_url') else None}...")
            print(f"  Has User: {reel.get('user') is not None}")
            print(f"  Views: {reel.get('views_count')}, Likes: {reel.get('likes_count')}")
    else:
        print(f"\nError Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("ERROR: Cannot connect to backend server!")
    print("Make sure backend is running on http://localhost:8082")
except Exception as e:
    print(f"ERROR: {e}")
