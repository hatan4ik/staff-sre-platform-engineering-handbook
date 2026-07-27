# AWS Interview Track — Official Primary Sources

This index grounds version-sensitive AWS claims in first-party documentation. Service limits and feature availability change; verify the linked documentation and the target account/Region before using any value in production or in a precise interview claim.

## Amazon EKS

- [Amazon EKS Best Practices Guide](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
- [Amazon EKS control-plane logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Amazon EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Monitor EKS with Prometheus](https://docs.aws.amazon.com/eks/latest/userguide/prometheus.html)
- [EKS log collector](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)

## Terraform

- [S3 backend and native lockfile](https://developer.hashicorp.com/terraform/language/backend/s3)
- [State locking](https://developer.hashicorp.com/terraform/language/state/locking)
- [Refresh-only mode](https://developer.hashicorp.com/terraform/tutorials/state/refresh)
- [Import existing resources](https://developer.hashicorp.com/terraform/language/import)
- [Moved blocks](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)

## Identity and mobile backend

- [Amazon Cognito user pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html)
- [Cognito multi-Region user-pool replication](https://docs.aws.amazon.com/cognito/latest/developerguide/multi-region-replication.html)
- [Cognito multi-Region considerations and limitations](https://docs.aws.amazon.com/cognito/latest/developerguide/multi-region-considerations.html)
- [Amazon SNS mobile push notifications](https://docs.aws.amazon.com/sns/latest/dg/sns-mobile-application-as-subscriber.html)
- [AWS End User Messaging Push](https://docs.aws.amazon.com/push-notifications/latest/userguide/what-is-service.html)
- [AWS IoT Core MQTT](https://docs.aws.amazon.com/iot/latest/developerguide/mqtt.html)
- [AWS IoT Device Shadow](https://docs.aws.amazon.com/iot/latest/developerguide/iot-device-shadows.html)

## Secure software and fleet updates

- [AWS IoT Device Management Jobs](https://docs.aws.amazon.com/iot/latest/developerguide/iot-jobs.html)
- [Job rollout and abort configuration](https://docs.aws.amazon.com/iot/latest/developerguide/job-rollout-abort.html)
- [Presigned S3 URLs in job documents](https://docs.aws.amazon.com/iot/latest/developerguide/create-manage-jobs.html)
- [AWS IoT Device Management Software Package Catalog](https://docs.aws.amazon.com/iot/latest/developerguide/software-package-catalog.html)
- [Package version lifecycle](https://docs.aws.amazon.com/iot/latest/developerguide/package-version-lifecycle.html)
- [AWS Signer concepts](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html)
- [AWS IoT device security](https://docs.aws.amazon.com/iot/latest/developerguide/iot-security-identity.html)

## Multi-Region recovery

- [AWS Well-Architected Disaster Recovery of Workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [Amazon Application Recovery Controller](https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route-53-recovery.html)
- [ARC routing controls](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)
- [ARC safety rules](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.safety-rules.html)
- [ARC readiness checks](https://docs.aws.amazon.com/r53recovery/latest/dg/readiness-checks.html)
- [ARC Region switch](https://docs.aws.amazon.com/r53recovery/latest/dg/region-switch.html)
- [ARC Region switch execution blocks](https://docs.aws.amazon.com/r53recovery/latest/dg/region-switch-concepts.html)
- [Global Accelerator endpoint health and traffic control](https://docs.aws.amazon.com/global-accelerator/latest/dg/introduction-components.html)
- [DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- [Aurora Global Database failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)
- [S3 replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [ECR private-registry replication](https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html)
- [Secrets Manager replication](https://docs.aws.amazon.com/secretsmanager/latest/userguide/replicate-secrets.html)

## Observability

- [Amazon CloudWatch Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html)
- [Application Signals service monitoring](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Services.html)
- [CloudWatch investigations](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Investigations.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [CloudWatch Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html)
- [CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [AWS Distro for OpenTelemetry](https://aws-otel.github.io/)
- [X-Ray service integrations and SDK/daemon maintenance notice](https://docs.aws.amazon.com/xray/latest/devguide/xray-services.html)
- [Migrating X-Ray instrumentation to OpenTelemetry](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-migration.html)
- [Amazon Managed Service for Prometheus](https://docs.aws.amazon.com/prometheus/latest/userguide/what-is-Amazon-Managed-Service-Prometheus.html)
- [AMP high-availability sample deduplication](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)
- [AMP Alertmanager](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-alert-manager.html)
- [Amazon Managed Grafana](https://docs.aws.amazon.com/grafana/latest/userguide/what-is-Amazon-Managed-Service-Grafana.html)
- [Managed Grafana alerting guidance](https://docs.aws.amazon.com/grafana/latest/userguide/v12-alerting-manage.html)
- [CloudTrail Event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)
- [CloudTrail Lake availability and migration notice](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html)

## DNS, networking, and request-path troubleshooting

- [Route 53 public DNS query logging](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/query-logs.html)
- [Route 53 Resolver query logging](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html)
- [Route 53 health checks and failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)
- [VPC Reachability Analyzer](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [Network Access Analyzer](https://docs.aws.amazon.com/vpc/latest/network-access-analyzer/what-is-network-access-analyzer.html)
- [Application Load Balancer metrics](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html)
- [Application Load Balancer access logs](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html)
- [AWS WAF logging](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)

## Streaming and event systems

- [Amazon Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/introduction.html)
- [Kinesis capacity modes](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html)
- [Kinesis on-demand streams](https://docs.aws.amazon.com/streams/latest/dev/how-do-i-size-a-stream.html#how-do-i-size-a-stream-on-demand)
- [Kinesis enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)
- [Kinesis producer batching](https://docs.aws.amazon.com/streams/latest/dev/developing-producers-with-sdk.html)
- [Lambda with Kinesis](https://docs.aws.amazon.com/lambda/latest/dg/with-kinesis.html)
- [Lambda partial batch response for streams](https://docs.aws.amazon.com/lambda/latest/dg/services-kinesis-batchfailurereporting.html)
- [Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- [Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [SNS subscription filter policies](https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html)
- [Amazon EventBridge event buses](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-bus.html)
- [EventBridge quotas](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-quota.html)
- [EventBridge archives and replay](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html)
- [AWS Glue Schema Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html)

## Reliability and operational excellence

- [AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)
- [Post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_post_incident_analysis.html)
- [Amazon Builders' Library](https://aws.amazon.com/builders-library/)

## Version-sensitive notes captured in the track

- The legacy X-Ray SDKs and daemon entered maintenance mode on February 25, 2026; use OpenTelemetry for new instrumentation.
- CloudTrail Lake closed to new customers on May 31, 2026; existing customers can continue, while new designs should use currently supported CloudWatch and durable CloudTrail analytics paths.
- Terraform's S3 backend supports native lockfiles; DynamoDB-based locking is deprecated in current HashiCorp documentation.
- Cognito multi-Region replication improves authentication continuity but does not remove application responsibility for routing, write authority, federation, and failover testing.
- Kinesis capacity mode names and throughput behavior are version-sensitive. Verify the current service documentation, quotas, Region support, and the workload's real partition-key distribution before quoting a capacity number.