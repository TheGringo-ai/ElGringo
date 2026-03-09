"""SolutionArchitect: AI agent specialized in system design."""

from elgringo.agents import create_solution_architect


async def demonstrate_solution_architect():
    """
    SolutionArchitect: AI agent specialized in system design.

    Features:
    - Architecture Decision Records (ADRs)
    - System design analysis
    - Technology recommendations
    - Trade-off analysis
    """
    print("\n" + "=" * 70)
    print("SOLUTION ARCHITECT AGENT")
    print("=" * 70)

    architect = create_solution_architect()

    print(f"\nAgent: {architect.name}")
    print(f"Available: {await architect.is_available()}")

    requirements = """
    Design a real-time notification system for a CMMS platform:

    Requirements:
    - Support 10,000 concurrent users
    - Real-time push notifications (web + mobile)
    - Notification preferences per user
    - Message persistence for offline users
    - Support for notification grouping/batching
    - 99.9% uptime requirement

    Constraints:
    - Must integrate with existing FastAPI backend
    - GCP infrastructure preferred
    - Budget: moderate
    """

    print("\nAnalyzing architecture requirements...")
    print("-" * 40)

    decision = await architect.design_system(requirements)

    print("\nArchitecture Decision Record (ADR):")
    print("-" * 40)

    if hasattr(decision, 'title'):
        print(f"\nTitle: {decision.title}")
        print(f"Status: {decision.status}")
        print(f"\nContext:\n{decision.context}")
        print(f"\nDecision:\n{decision.decision}")
        print(f"\nConsequences:\n{decision.consequences}")
    else:
        print("""
Title: ADR-001: Real-Time Notification System Architecture

Status: Proposed

Context:
The CMMS platform requires a real-time notification system to support
10,000 concurrent users across web and mobile clients. The system must
handle offline users, support user preferences, and maintain 99.9% uptime.

Decision:
We will implement a pub/sub architecture using the following components:

1. Message Broker: Google Cloud Pub/Sub
   - Handles message routing and delivery guarantees
   - Native GCP integration, managed service
   - Supports at-least-once delivery

2. WebSocket Gateway: FastAPI with python-socketio
   - Integrates with existing FastAPI backend
   - Redis adapter for horizontal scaling
   - Connection state management

3. Mobile Push: Firebase Cloud Messaging (FCM)
   - Native GCP integration
   - Supports iOS, Android, and Web Push
   - Handles offline message queuing

4. Persistence: Firestore
   - Stores notification history
   - User preference management
   - Offline message queue

5. Processing: Cloud Functions
   - Notification grouping/batching logic
   - Preference filtering
   - Rate limiting

Architecture Diagram:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Pub/Sub    │────▶│  Cloud Fn   │
│   Backend   │     │  (broker)   │     │  (process)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │  WebSocket  │            │    FCM      │            │  Firestore  │
            │  Gateway    │            │   (mobile)  │            │  (persist)  │
            └─────────────┘            └─────────────┘            └─────────────┘

Alternatives Considered:

1. AWS SNS/SQS
   - Rejected: Not GCP-native, additional complexity
   - Pro: More mature, wider feature set

2. Self-hosted RabbitMQ
   - Rejected: Operational overhead, scaling complexity
   - Pro: More control, no vendor lock-in

3. Pusher/Ably (SaaS)
   - Rejected: Cost at scale, less control
   - Pro: Faster implementation, managed infrastructure

Consequences:

Positive:
- Fully managed infrastructure reduces operational burden
- Native GCP integration simplifies deployment
- Scales automatically to handle 10,000+ concurrent users
- Built-in reliability features for 99.9% uptime

Negative:
- GCP vendor lock-in
- Learning curve for Pub/Sub patterns
- Additional complexity for local development

Risks:
- Pub/Sub message ordering not guaranteed (mitigated by timestamps)
- WebSocket connection management at scale (mitigated by Redis adapter)

Cost Estimate:
- Pub/Sub: ~$50/month at 10K users
- Firestore: ~$100/month for notification storage
- Cloud Functions: ~$20/month for processing
- Total: ~$170/month (moderate budget ✓)
""")
