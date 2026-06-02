import asyncio
import time
import json
from backend.services.scenario_expansion_service import expand_scenarios
from backend.services.action_translation_service import translate_test_case
from backend.ai.schema.test_plan_schema import TestCase
from backend.agent.browser_session import BrowserSessionManager
from backend.services.execution_service import run_test_steps

URL = "https://www.saucedemo.com/"
DOM = {"inputs": [], "buttons": [], "links": []}

FEATURE_ORDER = ["AUTHENTICATION", "INVENTORY", "CART", "CHECKOUT"]

async def main():
    mgr = BrowserSessionManager(headless=True)
    print("Starting browser manager...")
    await mgr.start()
    print("Browser manager started")
    shared_state = {}
    # perform quick DOM discovery so selectors can be resolved
    print("Performing DOM discovery...")
    discovery_session = await mgr.new_session()
    try:
        await discovery_session.page.goto(URL, wait_until="domcontentloaded")
        dom_inputs = await discovery_session.page.eval_on_selector_all('input', "nodes => nodes.map(n => ({name: n.name, placeholder: n.placeholder, id: n.id, aria_label: n.getAttribute('aria-label'), label: (n.labels && n.labels.length>0)? n.labels[0].innerText: null, type: n.type}))")
        dom_buttons = await discovery_session.page.eval_on_selector_all('button, input[type=submit], a', "nodes => nodes.map(n => ({text: n.innerText || n.value || n.getAttribute('aria-label') || '', aria_label: n.getAttribute('aria-label'), id: n.id, name: n.name, class: n.className, type: n.type}))")
        dom_links = await discovery_session.page.eval_on_selector_all('a', "nodes => nodes.map(n => ({text: n.innerText || '', href: n.href}))")
        DOM = {"inputs": dom_inputs or [], "buttons": dom_buttons or [], "links": dom_links or []}
    except Exception as e:
        print(f"DOM discovery failed: {e}")
    finally:
        try:
            await discovery_session.close()
        except Exception:
            pass

    plan = expand_scenarios(URL, "Run authentication and inventory smoke", DOM)

    # pick scenarios for features in order
    scenario_map = {s['feature_key'] + '::' + s['scenario_name']: s for s in plan.get('scenario_cases', [])}
    selected = []
    for fk in FEATURE_ORDER:
        found = None
        for s in plan.get('scenario_cases', []):
            if s.get('feature_key') == fk:
                # prefer valid_input/ inventory_load / cart_load / complete_workflow
                preferred = None
                if fk == 'AUTHENTICATION':
                    preferred = next((ss for ss in plan['scenario_cases'] if ss['feature_key']=='AUTHENTICATION' and ss['scenario_category']=='valid_input'), None)
                if fk == 'INVENTORY':
                    preferred = next((ss for ss in plan['scenario_cases'] if ss['feature_key']=='INVENTORY' and ss['scenario_category']=='inventory_load'), None)
                if fk == 'CART':
                    preferred = next((ss for ss in plan['scenario_cases'] if ss['feature_key']=='CART' and ss['scenario_category']=='cart_load'), None)
                if fk == 'CHECKOUT':
                    preferred = next((ss for ss in plan['scenario_cases'] if ss['feature_key']=='CHECKOUT' and ss['scenario_category']=='complete_workflow'), None)
                found = preferred or s
                break
        if found:
            selected.append(found)

    results = []
    overall_start = time.perf_counter()
    def progress_callback(payload):
        try:
            line = json.dumps(payload, default=str)
            print(line)
            with open('backend/scripts/saucedemo_progress.log', 'a', encoding='utf-8') as fh:
                fh.write(line + "\n")
        except Exception:
            try:
                s = str(payload)
                print(s)
                with open('backend/scripts/saucedemo_progress.log', 'a', encoding='utf-8') as fh:
                    fh.write(s + "\n")
            except Exception:
                pass

    def print_scenario_summary(scenario_name, res, attempt, elapsed):
        print(f"SCENARIO STATUS | {scenario_name} | attempt={attempt} | run_status={res.get('run_status')} | failed_tasks={res.get('failed_tasks')} | elapsed_s={elapsed:.1f}")
        print(f"FINAL URL | {res.get('final_url') or shared_state.get('final_url') or ''}")
        print(f"AUTHENTICATED STATE | {res.get('authenticated') if 'authenticated' in res else shared_state.get('authenticated', False)}")
        print(f"RECOVERY ATTEMPTS | {res.get('recovery_attempts', 0)}")
        step_results = res.get('results') or res.get('step_results') or []
        for index, step_result in enumerate(step_results, start=1):
            if not isinstance(step_result, dict):
                print(f"STEP STATUS | {index} | {step_result}")
                continue
            step_name = step_result.get('step_name') or step_result.get('name') or step_result.get('action') or 'step'
            step_status = step_result.get('status') or step_result.get('step_status') or step_result.get('run_status') or 'unknown'
            resolved_selector = step_result.get('resolved_selector') or step_result.get('selector') or ''
            print(f"STEP STATUS | {index} | {step_name} | {step_status} | selector={resolved_selector}")

    max_attempts = 10
    for scenario in selected:
        # Prepare test case translation once per scenario
        tc = TestCase(
            title=scenario.get('scenario_name'),
            expected=scenario.get('expected'),
            steps=scenario.get('steps') or [],
            objective_id=scenario.get('objective_id'),
            objective_name=scenario.get('objective_name'),
            feature_key=scenario.get('feature_key'),
            coverage_level=scenario.get('coverage_level'),
            scenario_id=scenario.get('scenario_id'),
            scenario_name=scenario.get('scenario_name'),
            scenario_category=scenario.get('scenario_category'),
            risk_score=scenario.get('risk_score'),
            risk_level=scenario.get('risk_level'),
            depends_on=scenario.get('depends_on') or [],
            required_state=scenario.get('required_state') or [],
            produces_state=scenario.get('produces_state') or [],
            required_page=scenario.get('required_page'),
        )
        translated, logs = translate_test_case(tc)

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            print(f"Attempt {attempt} for scenario: {translated.scenario_name}")

            # Ensure fresh DOM discovery before authentication attempt
            try:
                discovery_session = await mgr.new_session()
                await discovery_session.page.goto(URL, wait_until="domcontentloaded")
                dom_inputs = await discovery_session.page.eval_on_selector_all('input', "nodes => nodes.map(n => ({name: n.name, placeholder: n.placeholder, id: n.id, aria_label: n.getAttribute('aria-label'), label: (n.labels && n.labels.length>0)? n.labels[0].innerText: null, type: n.type}))")
                dom_buttons = await discovery_session.page.eval_on_selector_all('button, input[type=submit], a', "nodes => nodes.map(n => ({text: n.innerText || n.value || n.getAttribute('aria-label') || '', aria_label: n.getAttribute('aria-label'), id: n.id, name: n.name, class: n.className, type: n.type}))")
                dom_links = await discovery_session.page.eval_on_selector_all('a', "nodes => nodes.map(n => ({text: n.innerText || '', href: n.href}))")
                DOM = {"inputs": dom_inputs or [], "buttons": dom_buttons or [], "links": dom_links or []}
            except Exception as e:
                print(f"DOM discovery failed on attempt {attempt}: {e}")
            finally:
                try:
                    await discovery_session.close()
                except Exception:
                    pass

            start = time.perf_counter()
            print(f"Running scenario: {translated.scenario_name}")
            res = await run_test_steps(URL, translated, dom=DOM, progress_callback=progress_callback, shared_state=shared_state, session_manager=mgr)
            elapsed = time.perf_counter() - start

            # update shared_state from artifacts
            artifacts = res.get('artifacts') or {}
            if artifacts.get('storage_state'):
                shared_state['storage_state'] = artifacts.get('storage_state')
            if artifacts.get('session_storage'):
                shared_state['session_storage'] = artifacts.get('session_storage')
            if artifacts.get('previous_successful_actions'):
                shared_state['previous_successful_actions'] = artifacts.get('previous_successful_actions')
            if artifacts.get('authenticated') is not None:
                shared_state['authenticated'] = artifacts.get('authenticated')

            results.append({
                'feature': translated.feature_key,
                'scenario': translated.scenario_name,
                'run_status': res.get('run_status'),
                'total_steps': res.get('total_steps'),
                'failed_tasks': res.get('failed_tasks'),
                'metrics': {k: res.get(k) for k in ['recovery_attempts','successful_recoveries'] if k in res},
                'elapsed_s': elapsed,
                'results': res.get('results', [])
            })
            print_scenario_summary(translated.scenario_name, res, attempt, elapsed)

            # if any failed tasks, retry whole scenario up to max_attempts
            if res.get('failed_tasks'):
                print(f"Scenario {translated.scenario_name} failed on attempt {attempt}; will retry whole flow")
                if attempt >= max_attempts:
                    print(f"Reached max attempts ({max_attempts}) for scenario {translated.scenario_name}; stopping")
                    break
                else:
                    await asyncio.sleep(1)
                    continue
            else:
                # success for this scenario; proceed to next scenario
                break

    overall_elapsed = time.perf_counter() - overall_start
    await mgr.shutdown()
    summary = {
        'total_runtime_s': overall_elapsed,
        'per_scenario': results,
        'shared_state_final': shared_state,
    }
    print(json.dumps(summary, indent=2, default=str))

if __name__ == '__main__':
    asyncio.run(main())
