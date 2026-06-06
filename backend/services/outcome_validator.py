def validate_expected_outcome(
    expected: str,
    observation: dict
):

    combined = str(observation).lower()

    expected = expected.lower()

    return expected in combined