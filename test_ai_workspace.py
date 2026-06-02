import requests, json

def main():
    base = 'http://127.0.0.1:8000'
    signup_url = f'{base}/api/auth/signup'
    payload = {
        'email': 'test@example.com',
        'password': 'Password123',
        'name': 'Test User'
    }
    r = requests.post(signup_url, json=payload)
    print('Signup status:', r.status_code)
    if r.status_code != 200:
        print('Response:', r.text)
        return
    token = r.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    sessions_url = f'{base}/api/ai-workspace/sessions'
    r2 = requests.get(sessions_url, headers=headers)
    print('Sessions status:', r2.status_code)
    print('Sessions response:', r2.text)

if __name__ == '__main__':
    main()
