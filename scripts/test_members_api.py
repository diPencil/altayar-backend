#!/usr/bin/env python3
import requests
import os

os.environ['DATABASE_URL'] = 'sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db'

# Test the members endpoint
plan_id = '0ee07da5-3de6-4973-9a4f-2ea3de215c01'  # Silver plan
url = f'http://localhost:8001/api/memberships/plans/{plan_id}/members'

print(f'Testing endpoint: {url}')

try:
    response = requests.get(url, timeout=10)
    print(f'Status: {response.status_code}')

    if response.status_code == 200:
        data = response.json()
        print(f'Response keys: {list(data.keys())}')
        members = data.get('members', [])
        print(f'Members count: {len(members)}')
        print(f'Total members: {data.get("total_members", 0)}')

        if members:
            print('First member keys:', list(members[0].keys()))
            print('First member data:')
            for key, value in members[0].items():
                print(f'  {key}: {value}')
        else:
            print('No members found')
    else:
        print(f'Error: {response.text}')

except requests.exceptions.ConnectionError:
    print('❌ Server not running')
except Exception as e:
    print(f'❌ Error: {e}')
