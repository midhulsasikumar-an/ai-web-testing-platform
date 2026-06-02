from backend.services.selector_resolver import record_selector_success
print('invoking test write...')
try:
    record_selector_success('#test', 'test target', context={'page_url':'https://www.saucedemo.com'}, action='click', source='unit_test')
    print('invoked')
except Exception as e:
    print('exception thrown', repr(e))
