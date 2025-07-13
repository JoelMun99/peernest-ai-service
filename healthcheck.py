#!/usr/bin/env python3
import urllib.request
import urllib.error
import sys
import json

def health_check():
    try:
        # Try to access the health endpoint
        with urllib.request.urlopen('http://localhost:8000/health', timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data.get('status') == 'healthy':
                    print('Health check passed')
                    return 0
                else:
                    print('Health check failed: service not healthy')
                    return 1
            else:
                print(f'Health check failed with status: {response.status}')
                return 1
    except urllib.error.URLError as e:
        print(f'Health check error: {e}')
        return 1
    except Exception as e:
        print(f'Health check exception: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(health_check())