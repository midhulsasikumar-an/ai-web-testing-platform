import ast, sys
src = open('backend/services/execution_service.py').read()
literal = "Execution finished"
if literal in src:
    print('FAIL: still has "' + literal + '" literal')
    sys.exit(1)
print('OK: no "' + literal + '" literal in execution_service.py')
for m in ['Scenario finished: ', 'Scenario finished with failures: ', 'Scenario cancelled or timed out: ']:
    if m not in src:
        print('FAIL: missing message: ' + m)
        sys.exit(1)
print('OK: all three new messages present')
