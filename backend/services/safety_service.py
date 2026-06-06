from backend.agent.safety import SafetyPolicy


def is_same_domain(base_url: str, current_url: str):
    policy = SafetyPolicy.from_start_url(base_url, same_origin_only=True, allow_private_hosts=True)
    return policy.validate_navigation(base_url, current_url).valid
