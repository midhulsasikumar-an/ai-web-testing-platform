# AI Reporting Pipeline

- Inputs: execution artifacts (dom, console, network, screenshots, metadata)
- Detection: success_detector, network_analysis_service, visual_issue_service, bug_detection_service
- Aggregation: website_health_service computes score and aggregates issues
- Persistence: s3_storage uploads screenshots; final report references presigned URLs
- Output: AI-readable report with executive summary, sections and structured issues
