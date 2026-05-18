# Execution Pipeline

Describe how the planner/executor/validator interact and where detectors are invoked.

1. Planner creates the scenario and expectations.
2. Executor runs steps in a deterministic sequence and collects artifacts.
3. Validator (WebsiteHealthService) runs detectors and produces reports.
4. Reporter stores artifacts and generates final JSON report and presigned screenshots.
