import asyncio
import os
from backend.services.execution_service import run_test_steps
from backend.ai.schema.test_plan_schema import TestCase, Step

async def progress_callback(event):
    print("PROGRESS:", event.get('type'), event.get('message') or '')
    if event.get('type') == 'screenshot':
        b64 = event.get('screenshot_b64')
        if b64:
            data = b64.encode('ascii')
            import base64
            img = base64.b64decode(data)
            path = os.path.join('artifacts','debug_direct.png')
            os.makedirs('artifacts', exist_ok=True)
            with open(path, 'wb') as fh:
                fh.write(img)
            print('Saved screenshot to', path)

async def main():
    steps = [Step(action='click', target='Log In', selector='')]
    tc = TestCase(title='Direct Debug', expected='', steps=steps)
    res = await run_test_steps('http://localhost:3000/', tc, dom=None, credentials=None, progress_callback=progress_callback)
    print('RESULT:', res)

if __name__ == '__main__':
    asyncio.run(main())
