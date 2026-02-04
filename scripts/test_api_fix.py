#!/usr/bin/env python3
import requests

# Test the members endpoint with the Silver plan
plan_id = '0ee07da5-3de6-4973-9a4f-2ea3de215c01'
url = f'http://localhost:8001/api/memberships/plans/{plan_id}/members'

print(f'Testing: {url}')

try:
    response = requests.get(url, timeout=10)
    print(f'Status: {response.status_code}')

    if response.status_code == 200:
        data = response.json()
        plan = data.get('plan', {})
        members = data.get('members', [])
        print(f'Plan: {plan.get("tier_name_en")}')
        print(f'Members: {len(members)}')

        if members:
            print(f'First member: {members[0].get("name")}')
        print('✅ API working!')
    else:
        print(f'❌ Error: {response.text[:100]}')

except Exception as e:
    print(f'❌ Error: {e}')
