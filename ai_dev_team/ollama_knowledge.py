"""
Ollama Knowledge Enhancement System
====================================

Provides comprehensive knowledge injection for local Ollama models,
making them more capable agents for the AI Team Platform.

Features:
- Domain expertise prompts
- Tool usage knowledge
- Code pattern libraries
- Project context injection
- Best practices database
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExpertiseDomain(Enum):
    """Domain expertise areas"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    REACT = "react"
    FASTAPI = "fastapi"
    FIREBASE = "firebase"
    DOCKER = "docker"
    GIT = "git"
    TESTING = "testing"
    SECURITY = "security"
    DATABASE = "database"
    DEVOPS = "devops"
    MOBILE = "mobile"
    AI_ML = "ai_ml"
    CLOUD = "cloud"
    KUBERNETES = "kubernetes"
    TERRAFORM = "terraform"
    GCP = "gcp"
    AWS = "aws"
    # Frontend-specific domains
    NEXTJS = "nextjs"
    VUE = "vue"
    SVELTE = "svelte"
    TAILWIND = "tailwind"
    STATE = "state"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    CSS = "css"
    BUILD = "build"
    ASTRO = "astro"
    SHADCN = "shadcn"


@dataclass
class KnowledgeEntry:
    """A piece of knowledge for the model"""
    domain: str
    topic: str
    content: str
    examples: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher = more important
    tags: List[str] = field(default_factory=list)


class OllamaKnowledgeBase:
    """
    Comprehensive knowledge base for enhancing Ollama models.

    Provides:
    - System prompts with expert knowledge
    - Tool usage documentation
    - Code patterns and best practices
    - Project-specific context
    """

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path) if project_path else None
        self._knowledge: Dict[str, List[KnowledgeEntry]] = {}
        self._tool_docs: Dict[str, str] = {}
        self._load_default_knowledge()
        self._load_tool_documentation()

    def _load_default_knowledge(self):
        """Load built-in knowledge base"""

        # Python expertise
        self._add_knowledge(KnowledgeEntry(
            domain="python",
            topic="Best Practices",
            content="""Python Best Practices:
1. Use type hints for all function signatures
2. Prefer pathlib over os.path for file operations
3. Use context managers (with statements) for resources
4. Use dataclasses or Pydantic for data structures
5. Prefer f-strings over .format() or % formatting
6. Use logging instead of print for debugging
7. Follow PEP 8 style guidelines
8. Use virtual environments for project isolation
9. Write docstrings for public functions/classes
10. Handle exceptions specifically, not bare except""",
            examples=[
                "from pathlib import Path\npath = Path('file.txt')",
                "def greet(name: str) -> str:\n    return f'Hello, {name}'",
            ],
            priority=9,
            tags=["python", "style", "best-practices"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="python",
            topic="Async Programming",
            content="""Python Async/Await Patterns:
1. Use async def for I/O-bound operations
2. Use asyncio.gather() for parallel execution
3. Use asyncio.create_task() for background tasks
4. Always await coroutines, never call them directly
5. Use async context managers (async with)
6. Use aiohttp for async HTTP requests
7. Use asyncio.Queue for producer-consumer patterns
8. Handle cancellation with try/except asyncio.CancelledError""",
            examples=[
                "async def fetch_all(urls):\n    return await asyncio.gather(*[fetch(u) for u in urls])",
            ],
            priority=8,
            tags=["python", "async", "concurrency"]
        ))

        # FastAPI expertise
        self._add_knowledge(KnowledgeEntry(
            domain="fastapi",
            topic="API Development",
            content="""FastAPI Best Practices:
1. Use Pydantic models for request/response validation
2. Use Depends() for dependency injection
3. Use HTTPException for error responses
4. Use BackgroundTasks for async operations
5. Use APIRouter for route organization
6. Set proper status codes (201 for create, 204 for delete)
7. Use response_model for automatic serialization
8. Use tags for API documentation organization
9. For HTML pages, use cookie auth (get_current_user_from_cookie)
10. For API endpoints, use OAuth2 Bearer token auth""",
            examples=[
                "@app.post('/items', status_code=201)\nasync def create_item(item: Item):\n    return item",
                "from fastapi import Depends, HTTPException\n\nasync def get_user(token: str = Depends(oauth2_scheme)):\n    user = verify_token(token)\n    if not user:\n        raise HTTPException(401, 'Invalid token')\n    return user",
            ],
            priority=9,
            tags=["fastapi", "api", "python"]
        ))

        # Firebase expertise
        self._add_knowledge(KnowledgeEntry(
            domain="firebase",
            topic="Firestore Operations",
            content="""Firebase/Firestore Best Practices:
1. Always filter by organization_id for multi-tenant data
2. Use batch writes for multiple document updates
3. Create composite indexes for filter + orderBy queries
4. Use server timestamps: firestore.SERVER_TIMESTAMP
5. Use transactions for atomic operations
6. Limit query results with .limit()
7. Use subcollections for 1:many relationships
8. Store denormalized data to reduce reads
9. Use Firebase Admin SDK on server, JS SDK on client
10. Never expose service account keys in client code""",
            examples=[
                "# Always include organization_id\nquery = db.collection('work_orders').where('organization_id', '==', org_id)",
                "# Batch write\nbatch = db.batch()\nfor doc in docs:\n    batch.set(db.collection('items').document(), doc)\nawait batch.commit()",
            ],
            priority=9,
            tags=["firebase", "firestore", "database"]
        ))

        # React/TypeScript expertise
        self._add_knowledge(KnowledgeEntry(
            domain="react",
            topic="React Native Development",
            content="""React Native Best Practices:
1. Use functional components with hooks
2. Use TypeScript for type safety
3. Use React.memo() for performance optimization
4. Use useCallback for stable function references
5. Use useMemo for expensive computations
6. Use AsyncStorage for local persistence
7. Handle offline scenarios gracefully
8. Use FlatList for long lists (not ScrollView)
9. Test on both iOS and Android
10. Use Expo for easier development workflow""",
            examples=[
                "const MyComponent = React.memo(({ data }) => {\n  return <Text>{data.name}</Text>;\n});",
            ],
            priority=8,
            tags=["react", "mobile", "typescript"]
        ))

        # Git expertise
        self._add_knowledge(KnowledgeEntry(
            domain="git",
            topic="Git Workflow",
            content="""Git Best Practices:
1. Write clear, concise commit messages
2. Use feature branches for new work
3. Keep commits atomic and focused
4. Never force push to main/master
5. Use pull requests for code review
6. Rebase feature branches before merging
7. Use .gitignore for build artifacts and secrets
8. Tag releases with semantic versioning
9. Sign commits for security
10. Never commit secrets or credentials""",
            examples=[
                "git checkout -b feature/add-auth\ngit add -p  # Stage specific hunks\ngit commit -m 'Add JWT authentication'",
            ],
            priority=8,
            tags=["git", "version-control", "workflow"]
        ))

        # Docker expertise
        self._add_knowledge(KnowledgeEntry(
            domain="docker",
            topic="Container Best Practices",
            content="""Docker Best Practices:
1. Use multi-stage builds for smaller images
2. Use specific base image tags, not :latest
3. Order Dockerfile commands for better caching
4. Use .dockerignore to exclude unnecessary files
5. Run as non-root user for security
6. Use health checks for container monitoring
7. Set resource limits (memory, CPU)
8. Use docker-compose for multi-container apps
9. Clean up unused images/containers regularly
10. Use secrets management, not environment variables""",
            examples=[
                "# Multi-stage build\nFROM python:3.11 AS builder\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\n\nFROM python:3.11-slim\nCOPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11",
            ],
            priority=8,
            tags=["docker", "containers", "devops"]
        ))

        # Security expertise
        self._add_knowledge(KnowledgeEntry(
            domain="security",
            topic="Application Security",
            content="""Security Best Practices:
1. Never trust user input - always validate
2. Use parameterized queries to prevent SQL injection
3. Escape output to prevent XSS
4. Use HTTPS everywhere
5. Implement proper authentication (JWT, OAuth2)
6. Use secure session management
7. Apply principle of least privilege
8. Keep dependencies updated
9. Log security events for monitoring
10. Never store passwords in plain text - use bcrypt/argon2""",
            examples=[
                "# Parameterized query\ncursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                "# Password hashing\nfrom passlib.hash import bcrypt\nhashed = bcrypt.hash(password)",
            ],
            priority=10,
            tags=["security", "authentication", "best-practices"]
        ))

        # Testing expertise
        self._add_knowledge(KnowledgeEntry(
            domain="testing",
            topic="Testing Strategies",
            content="""Testing Best Practices:
1. Write tests before fixing bugs (TDD for bugs)
2. Use pytest for Python testing
3. Mock external dependencies
4. Test edge cases and error conditions
5. Use fixtures for test data
6. Aim for high coverage but prioritize critical paths
7. Use integration tests for API endpoints
8. Test async code with pytest-asyncio
9. Use factories for test data generation
10. Run tests in CI/CD pipeline""",
            examples=[
                "@pytest.fixture\ndef user():\n    return User(name='Test', email='test@example.com')\n\ndef test_user_creation(user):\n    assert user.name == 'Test'",
            ],
            priority=8,
            tags=["testing", "pytest", "quality"]
        ))

        # =====================
        # MOBILE DEVELOPMENT
        # =====================

        self._add_knowledge(KnowledgeEntry(
            domain="mobile",
            topic="React Native Best Practices",
            content="""React Native Best Practices:
1. Use functional components with hooks (useState, useEffect, useMemo, useCallback)
2. Use TypeScript for type safety and better developer experience
3. Use FlatList for long lists, never ScrollView with many items
4. Implement proper navigation with React Navigation
5. Use AsyncStorage for local persistence
6. Handle offline scenarios with NetInfo and queues
7. Use React.memo() for performance optimization
8. Implement proper error boundaries
9. Use Expo for easier development and OTA updates
10. Test on both iOS and Android simultaneously
11. Use platform-specific code when needed: Platform.OS === 'ios'
12. Optimize images with proper sizing and caching""",
            examples=[
                "import { FlatList } from 'react-native';\n<FlatList data={items} renderItem={({item}) => <Item {...item}/>} keyExtractor={item => item.id}/>",
                "const [data, setData] = useState<Item[]>([]);\nuseEffect(() => {\n  loadData().then(setData);\n}, []);",
            ],
            priority=9,
            tags=["mobile", "react-native", "expo"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="mobile",
            topic="iOS Development",
            content="""iOS Development Patterns:
1. Use SwiftUI for new UI development
2. Implement MVVM architecture pattern
3. Use Combine for reactive programming
4. Handle app lifecycle properly (background, foreground)
5. Use Core Data or Realm for local storage
6. Implement proper push notification handling
7. Use async/await for asynchronous code
8. Follow Human Interface Guidelines (HIG)
9. Use URLSession for networking
10. Implement proper keychain storage for sensitive data""",
            examples=[
                "@State private var items: [Item] = []\n\nvar body: some View {\n    List(items) { item in\n        Text(item.name)\n    }\n}",
            ],
            priority=7,
            tags=["mobile", "ios", "swift"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="mobile",
            topic="Android Development",
            content="""Android Development Patterns:
1. Use Jetpack Compose for modern UI
2. Follow MVVM with ViewModel and LiveData
3. Use Kotlin Coroutines for async operations
4. Implement Room for local database
5. Use Retrofit for network calls
6. Handle configuration changes properly
7. Use WorkManager for background tasks
8. Follow Material Design guidelines
9. Implement proper dependency injection (Hilt/Dagger)
10. Use DataStore for preferences (replaces SharedPreferences)""",
            examples=[
                "@Composable\nfun ItemList(items: List<Item>) {\n    LazyColumn {\n        items(items) { item ->\n            Text(text = item.name)\n        }\n    }\n}",
            ],
            priority=7,
            tags=["mobile", "android", "kotlin"]
        ))

        # =====================
        # AI/ML DEVELOPMENT
        # =====================

        self._add_knowledge(KnowledgeEntry(
            domain="ai_ml",
            topic="Machine Learning Best Practices",
            content="""Machine Learning Best Practices:
1. Always split data into train/validation/test sets
2. Use cross-validation for model evaluation
3. Normalize/standardize input features
4. Handle missing data appropriately
5. Use appropriate metrics (accuracy, F1, AUC-ROC, MAE)
6. Implement proper feature engineering
7. Use early stopping to prevent overfitting
8. Save model checkpoints during training
9. Version your models and datasets
10. Document hyperparameters and experiments
11. Use MLflow or Weights & Biases for experiment tracking
12. Implement proper model serving with FastAPI or TensorFlow Serving""",
            examples=[
                "from sklearn.model_selection import train_test_split\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)",
                "from sklearn.preprocessing import StandardScaler\nscaler = StandardScaler()\nX_scaled = scaler.fit_transform(X_train)",
            ],
            priority=9,
            tags=["ai", "ml", "machine-learning"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="ai_ml",
            topic="PyTorch Development",
            content="""PyTorch Best Practices:
1. Use DataLoader for efficient batch processing
2. Move tensors to GPU with .to(device)
3. Use torch.no_grad() for inference
4. Implement custom Dataset classes for data loading
5. Use nn.Module for model architecture
6. Save models with torch.save(model.state_dict(), path)
7. Use mixed precision training for speed (torch.cuda.amp)
8. Implement proper gradient clipping
9. Use learning rate schedulers
10. Profile with torch.profiler for optimization""",
            examples=[
                "class MyModel(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.fc = nn.Linear(784, 10)\n    def forward(self, x):\n        return self.fc(x.flatten(1))",
                "with torch.no_grad():\n    predictions = model(test_data)",
            ],
            priority=8,
            tags=["ai", "pytorch", "deep-learning"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="ai_ml",
            topic="LLM Development",
            content="""LLM/AI Agent Development:
1. Use structured prompts with clear instructions
2. Implement proper context window management
3. Use temperature settings appropriately (0 for deterministic, higher for creative)
4. Implement retry logic with exponential backoff
5. Cache responses for repeated queries
6. Use streaming for long responses
7. Implement proper token counting
8. Use function calling for tool use
9. Implement RAG (Retrieval Augmented Generation) for knowledge
10. Monitor costs and usage
11. Implement proper error handling for API failures
12. Use async/await for concurrent API calls""",
            examples=[
                "async def get_completion(prompt: str, max_retries: int = 3):\n    for i in range(max_retries):\n        try:\n            return await client.chat.completions.create(...)\n        except RateLimitError:\n            await asyncio.sleep(2 ** i)",
            ],
            priority=10,
            tags=["ai", "llm", "agents", "gpt"]
        ))

        # =====================
        # DEVOPS
        # =====================

        self._add_knowledge(KnowledgeEntry(
            domain="devops",
            topic="CI/CD Best Practices",
            content="""CI/CD Best Practices:
1. Automate everything - builds, tests, deployments
2. Use declarative pipeline definitions (YAML)
3. Run tests in parallel for speed
4. Implement branch protection rules
5. Use semantic versioning for releases
6. Implement proper secrets management
7. Use caching for dependencies and build artifacts
8. Implement blue/green or canary deployments
9. Set up proper monitoring and alerting
10. Use infrastructure as code (Terraform, Pulumi)
11. Implement rollback capabilities
12. Run security scans in pipeline (SAST, DAST)""",
            examples=[
                "# GitHub Actions\nname: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm test",
            ],
            priority=9,
            tags=["devops", "cicd", "automation"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="devops",
            topic="Monitoring and Observability",
            content="""Monitoring Best Practices:
1. Implement the three pillars: logs, metrics, traces
2. Use structured logging (JSON format)
3. Set up proper alerting thresholds
4. Implement distributed tracing for microservices
5. Use dashboards for visibility (Grafana, DataDog)
6. Monitor golden signals: latency, traffic, errors, saturation
7. Implement health check endpoints
8. Set up on-call rotations and runbooks
9. Use log aggregation (ELK, Loki)
10. Implement SLOs and error budgets""",
            examples=[
                "import structlog\nlogger = structlog.get_logger()\nlogger.info('request_processed', user_id=123, duration_ms=45)",
                "@app.get('/health')\ndef health():\n    return {'status': 'healthy', 'version': '1.0.0'}",
            ],
            priority=8,
            tags=["devops", "monitoring", "observability"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="devops",
            topic="Kubernetes Operations",
            content="""Kubernetes Best Practices:
1. Use namespaces for environment isolation
2. Set resource requests and limits
3. Implement proper health probes (liveness, readiness)
4. Use ConfigMaps and Secrets for configuration
5. Implement horizontal pod autoscaling (HPA)
6. Use persistent volumes for stateful data
7. Implement proper RBAC for security
8. Use Helm charts for templating
9. Implement pod disruption budgets
10. Use network policies for pod-to-pod security
11. Implement proper logging and monitoring
12. Use init containers for setup tasks""",
            examples=[
                "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 3\n  template:\n    spec:\n      containers:\n      - name: app\n        resources:\n          requests:\n            memory: '256Mi'\n            cpu: '100m'\n          limits:\n            memory: '512Mi'\n            cpu: '500m'",
            ],
            priority=9,
            tags=["devops", "kubernetes", "k8s"]
        ))

        # =====================
        # CLOUD PLATFORMS
        # =====================

        self._add_knowledge(KnowledgeEntry(
            domain="cloud",
            topic="Google Cloud Platform (GCP)",
            content="""GCP Best Practices:
1. Use Cloud Run for serverless containers
2. Use Cloud Functions for event-driven workloads
3. Use Firestore for NoSQL, Cloud SQL for relational
4. Implement proper IAM roles (principle of least privilege)
5. Use Secret Manager for sensitive data
6. Use Cloud Build for CI/CD
7. Implement Cloud Logging and Monitoring
8. Use Cloud Storage for objects, with proper lifecycle policies
9. Use VPC for network isolation
10. Enable Cloud Armor for DDoS protection
11. Use Cloud CDN for static content
12. Implement Cloud Tasks for async processing""",
            examples=[
                "# Deploy to Cloud Run\ngcloud run deploy myservice --source . --region us-central1 --allow-unauthenticated",
                "# Access secret\nfrom google.cloud import secretmanager\nclient = secretmanager.SecretManagerServiceClient()\nresponse = client.access_secret_version(name=f'projects/{project}/secrets/{secret}/versions/latest')",
            ],
            priority=9,
            tags=["cloud", "gcp", "google"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="cloud",
            topic="Amazon Web Services (AWS)",
            content="""AWS Best Practices:
1. Use Lambda for serverless compute
2. Use ECS/EKS for container orchestration
3. Use RDS for relational databases
4. Use DynamoDB for NoSQL workloads
5. Implement proper IAM policies (least privilege)
6. Use Secrets Manager or Parameter Store for secrets
7. Use CloudWatch for logging and monitoring
8. Use S3 for object storage with proper bucket policies
9. Implement VPC with proper subnet design
10. Use CloudFront for CDN
11. Use SQS/SNS for messaging
12. Use API Gateway for REST APIs""",
            examples=[
                "# Lambda handler\ndef handler(event, context):\n    return {'statusCode': 200, 'body': json.dumps({'message': 'Hello'})}",
                "# Boto3 S3\nimport boto3\ns3 = boto3.client('s3')\ns3.upload_file('file.txt', 'bucket', 'key')",
            ],
            priority=8,
            tags=["cloud", "aws", "amazon"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="cloud",
            topic="Terraform Infrastructure as Code",
            content="""Terraform Best Practices:
1. Use modules for reusable infrastructure
2. Use remote state backend (S3, GCS)
3. Implement state locking with DynamoDB/GCS
4. Use workspaces for environment separation
5. Use variables and locals for configuration
6. Implement proper resource naming conventions
7. Use data sources for existing resources
8. Implement proper dependency management
9. Use terraform fmt and validate in CI
10. Use terraform plan before apply
11. Implement proper tagging strategy
12. Use lifecycle blocks for critical resources""",
            examples=[
                "resource \"google_cloud_run_service\" \"default\" {\n  name     = \"my-service\"\n  location = \"us-central1\"\n  template {\n    spec {\n      containers {\n        image = \"gcr.io/my-project/my-image\"\n      }\n    }\n  }\n}",
                "terraform {\n  backend \"gcs\" {\n    bucket = \"my-terraform-state\"\n    prefix = \"terraform/state\"\n  }\n}",
            ],
            priority=9,
            tags=["cloud", "terraform", "iac"]
        ))

        # =====================
        # FRONTEND DEVELOPMENT
        # =====================

        self._add_knowledge(KnowledgeEntry(
            domain="react",
            topic="React 19 Features",
            content="""React 19 Best Practices:
1. Use React Server Components (RSC) for data fetching - they run on server only
2. Use 'use client' directive only when you need interactivity
3. Use the 'use' hook to read resources (promises, context) in render
4. Use Actions for form submissions - they work on both client and server
5. Use useOptimistic for optimistic UI updates
6. Use useFormStatus to show loading states in forms
7. Use useActionState to manage action state
8. Suspense boundaries for loading states - wrap async components
9. React Compiler (experimental) auto-memoizes - less useMemo/useCallback needed
10. Use ref as a prop directly - no need for forwardRef in many cases
11. Document metadata can be set with <title>, <meta>, <link> in components
12. Asset loading with preload, preinit for fonts and scripts""",
            examples=[
                "// Server Component (default in App Router)\nasync function UserProfile({ id }) {\n  const user = await fetchUser(id);\n  return <h1>{user.name}</h1>;\n}",
                "// Client Component with action\n'use client';\nimport { useFormStatus } from 'react-dom';\n\nfunction SubmitButton() {\n  const { pending } = useFormStatus();\n  return <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>;\n}",
                "// Optimistic updates\nconst [optimisticItems, addOptimisticItem] = useOptimistic(\n  items,\n  (state, newItem) => [...state, { ...newItem, sending: true }]\n);",
            ],
            priority=10,
            tags=["react", "react-19", "server-components", "actions"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="nextjs",
            topic="Next.js 15 App Router",
            content="""Next.js 15 Best Practices:
1. Use App Router (app/) - it's the future, uses React Server Components
2. Use layout.tsx for shared layouts - they don't re-render on navigation
3. Use loading.tsx for loading UI (wraps in Suspense automatically)
4. Use error.tsx for error boundaries per route segment
5. Use route.ts for API routes in app/api/
6. Use Server Actions for mutations - define with 'use server'
7. Use generateMetadata for dynamic SEO
8. Use generateStaticParams for static generation
9. Cache aggressively with unstable_cache and revalidate
10. Use next/image with priority for LCP images
11. Use next/font for zero-layout-shift fonts
12. Parallel routes with @folder for complex layouts
13. Intercepting routes with (.) for modals
14. Use Turbopack for faster dev (next dev --turbo)""",
            examples=[
                "// Server Action in component\nasync function createTodo(formData: FormData) {\n  'use server';\n  const title = formData.get('title');\n  await db.todos.create({ title });\n  revalidatePath('/todos');\n}",
                "// Dynamic metadata\nexport async function generateMetadata({ params }): Promise<Metadata> {\n  const product = await getProduct(params.id);\n  return { title: product.name, description: product.description };\n}",
                "// Route handler with caching\nexport async function GET(request: Request) {\n  const data = await fetch('...', { next: { revalidate: 3600 } });\n  return Response.json(data);\n}",
            ],
            priority=10,
            tags=["nextjs", "next-15", "app-router", "server-actions"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="vue",
            topic="Vue 3 Composition API",
            content="""Vue 3 Best Practices:
1. Use <script setup> for cleaner component syntax
2. Use ref() for primitives, reactive() for objects
3. Use computed() for derived state
4. Use watchEffect() for side effects that auto-track dependencies
5. Use watch() when you need old/new values or specific sources
6. Use composables (use* functions) for reusable logic
7. Use defineProps<T>() with TypeScript for typed props
8. Use defineEmits<T>() for typed events
9. Use provide/inject for dependency injection
10. Use Pinia for state management (replaces Vuex)
11. Use VueUse for common composables
12. Use Teleport for portals (modals, tooltips)
13. Use Suspense with async components""",
            examples=[
                "<script setup lang=\"ts\">\nimport { ref, computed } from 'vue';\n\nconst count = ref(0);\nconst doubled = computed(() => count.value * 2);\nconst increment = () => count.value++;\n</script>",
                "// Composable pattern\nexport function useCounter(initial = 0) {\n  const count = ref(initial);\n  const increment = () => count.value++;\n  const decrement = () => count.value--;\n  return { count, increment, decrement };\n}",
                "// Pinia store\nexport const useUserStore = defineStore('user', () => {\n  const user = ref<User | null>(null);\n  const isLoggedIn = computed(() => !!user.value);\n  async function login(email: string, password: string) {\n    user.value = await authService.login(email, password);\n  }\n  return { user, isLoggedIn, login };\n});",
            ],
            priority=9,
            tags=["vue", "vue-3", "composition-api", "pinia"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="svelte",
            topic="Svelte 5 Runes",
            content="""Svelte 5 Best Practices:
1. Use $state rune for reactive state (replaces let)
2. Use $derived rune for computed values (replaces $:)
3. Use $effect rune for side effects (replaces $: with side effects)
4. Use $props rune for component props
5. Use $bindable for two-way binding props
6. Use $inspect for debugging reactive values
7. Runes work in .svelte.ts files too for reusable logic
8. Use snippets for reusable template chunks
9. Event handlers now use onclick not on:click
10. Universal reactivity - works anywhere, not just components
11. Fine-grained reactivity - only what changes re-renders
12. Use SvelteKit for full-stack apps""",
            examples=[
                "// Svelte 5 with runes\n<script>\n  let count = $state(0);\n  let doubled = $derived(count * 2);\n  \n  $effect(() => {\n    console.log('Count changed:', count);\n  });\n</script>\n\n<button onclick={() => count++}>\n  {count} (doubled: {doubled})\n</button>",
                "// Props with $props\n<script>\n  let { name, age = 0 } = $props<{ name: string; age?: number }>();\n</script>",
                "// Reusable reactive logic (.svelte.ts)\nexport function createCounter(initial = 0) {\n  let count = $state(initial);\n  return {\n    get count() { return count; },\n    increment: () => count++,\n    decrement: () => count--,\n  };\n}",
            ],
            priority=8,
            tags=["svelte", "svelte-5", "runes", "sveltekit"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="tailwind",
            topic="Tailwind CSS 4",
            content="""Tailwind CSS 4 Best Practices:
1. Use the new CSS-first configuration (tailwind.config.ts optional)
2. Native CSS cascade layers for better specificity control
3. Container queries with @container and @min-*, @max-*
4. Built-in color-mix() for dynamic colors
5. Subgrid support with grid-rows-subgrid, grid-cols-subgrid
6. Use arbitrary values sparingly: [color:var(--custom)]
7. Group variants: group-hover:text-white
8. Peer variants for sibling styling: peer-checked:text-green-500
9. Use @apply sparingly - prefer utility classes in markup
10. Use cn() or clsx() for conditional classes
11. Configure content paths for proper purging
12. Use plugins for custom utilities and components
13. Dark mode with class strategy for user preference
14. Use prose class from @tailwindcss/typography for rich text""",
            examples=[
                "// Modern Tailwind component\nfunction Card({ className, children }) {\n  return (\n    <div className={cn(\n      'rounded-xl border bg-card p-6 shadow-sm',\n      'hover:shadow-md transition-shadow',\n      'dark:bg-card-dark dark:border-gray-800',\n      className\n    )}>\n      {children}\n    </div>\n  );\n}",
                "// Container queries\n<div className=\"@container\">\n  <div className=\"@md:grid-cols-2 @lg:grid-cols-3 grid gap-4\">\n    {items.map(item => <Card key={item.id} {...item} />)}\n  </div>\n</div>",
                "// Group and peer variants\n<label className=\"group flex items-center gap-2\">\n  <input type=\"checkbox\" className=\"peer\" />\n  <span className=\"peer-checked:text-green-500 peer-checked:line-through\">\n    Task\n  </span>\n</label>",
            ],
            priority=10,
            tags=["tailwind", "tailwind-4", "css", "utility-first"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="typescript",
            topic="TypeScript for Frontend",
            content="""TypeScript Frontend Best Practices:
1. Use strict mode in tsconfig.json
2. Use interface for object shapes, type for unions/intersections
3. Use discriminated unions for state machines
4. Use as const for literal types
5. Use generics for reusable components
6. Use React.ComponentProps<typeof Component> for extending props
7. Use satisfies for type checking without widening
8. Use NonNullable, Pick, Omit, Partial utility types
9. Use Zod for runtime validation with type inference
10. Never use 'any' - prefer 'unknown' and narrow
11. Use ReturnType<typeof fn> for function return types
12. Use Parameters<typeof fn> for function parameters
13. Configure paths in tsconfig for clean imports""",
            examples=[
                "// Discriminated union for state\ntype AsyncState<T> =\n  | { status: 'idle' }\n  | { status: 'loading' }\n  | { status: 'success'; data: T }\n  | { status: 'error'; error: Error };",
                "// Component props with generics\ninterface ListProps<T> {\n  items: T[];\n  renderItem: (item: T) => React.ReactNode;\n  keyExtractor: (item: T) => string;\n}\n\nfunction List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {\n  return items.map(item => (\n    <div key={keyExtractor(item)}>{renderItem(item)}</div>\n  ));\n}",
                "// Zod with TypeScript\nimport { z } from 'zod';\n\nconst UserSchema = z.object({\n  name: z.string().min(1),\n  email: z.string().email(),\n  age: z.number().positive().optional(),\n});\n\ntype User = z.infer<typeof UserSchema>;",
            ],
            priority=9,
            tags=["typescript", "frontend", "react", "types"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="state",
            topic="State Management",
            content="""Frontend State Management Best Practices:
1. Use TanStack Query (React Query) for server state
2. Use Zustand for simple client state
3. Use Jotai for atomic state (bottom-up)
4. Use Redux Toolkit only for complex global state
5. Colocate state as low as possible in the tree
6. Server state != client state - don't mix them
7. Use query invalidation for cache updates
8. Use optimistic updates for better UX
9. Use suspense mode with React 19 features
10. Persist state to localStorage when needed
11. Use devtools for debugging (React Query, Zustand, Redux)
12. Avoid prop drilling - but don't over-globalize""",
            examples=[
                "// TanStack Query\nconst { data, isLoading, error } = useQuery({\n  queryKey: ['users', userId],\n  queryFn: () => fetchUser(userId),\n  staleTime: 5 * 60 * 1000, // 5 minutes\n});",
                "// Zustand store\nimport { create } from 'zustand';\n\nconst useCartStore = create((set) => ({\n  items: [],\n  addItem: (item) => set((state) => ({\n    items: [...state.items, item]\n  })),\n  clearCart: () => set({ items: [] }),\n}));",
                "// Mutation with optimistic update\nconst mutation = useMutation({\n  mutationFn: updateTodo,\n  onMutate: async (newTodo) => {\n    await queryClient.cancelQueries(['todos']);\n    const previous = queryClient.getQueryData(['todos']);\n    queryClient.setQueryData(['todos'], (old) => [...old, newTodo]);\n    return { previous };\n  },\n  onError: (err, vars, context) => {\n    queryClient.setQueryData(['todos'], context.previous);\n  },\n});",
            ],
            priority=9,
            tags=["state", "react-query", "zustand", "tanstack"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="performance",
            topic="Web Performance & Core Web Vitals",
            content="""Web Performance Best Practices:
1. Optimize LCP (Largest Contentful Paint): < 2.5s
   - Preload critical images with priority
   - Use next/image or optimized images
   - Minimize render-blocking resources
2. Optimize INP (Interaction to Next Paint): < 200ms
   - Break up long tasks (< 50ms per task)
   - Use startTransition for non-urgent updates
   - Debounce/throttle event handlers
3. Optimize CLS (Cumulative Layout Shift): < 0.1
   - Set explicit width/height on images
   - Use next/font for zero-shift fonts
   - Avoid inserting content above existing content
4. Code splitting with dynamic imports
5. Lazy load below-the-fold images
6. Use Suspense for streaming SSR
7. Prefetch routes on hover/focus
8. Use service workers for caching
9. Minimize JavaScript bundle size
10. Use modern image formats (WebP, AVIF)""",
            examples=[
                "// Code splitting\nconst HeavyComponent = dynamic(() => import('./HeavyComponent'), {\n  loading: () => <Skeleton />,\n  ssr: false,\n});",
                "// Preload critical resources\n<Head>\n  <link rel=\"preload\" href=\"/fonts/inter.woff2\" as=\"font\" crossOrigin=\"\" />\n  <link rel=\"preconnect\" href=\"https://api.example.com\" />\n</Head>",
                "// Non-urgent state update\nstartTransition(() => {\n  setSearchResults(filterResults(query));\n});",
            ],
            priority=10,
            tags=["performance", "core-web-vitals", "lcp", "inp", "cls"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="accessibility",
            topic="Accessibility (WCAG 2.2)",
            content="""Accessibility Best Practices (WCAG 2.2):
1. Use semantic HTML: <button>, <nav>, <main>, <article>
2. All images need alt text (decorative: alt="")
3. Ensure 4.5:1 contrast ratio for text (3:1 for large text)
4. All interactive elements must be keyboard accessible
5. Focus indicators must be visible (don't remove outline)
6. Use aria-label/aria-labelledby for custom controls
7. Use aria-live for dynamic content updates
8. Skip links for keyboard navigation
9. Don't use color alone to convey information
10. Ensure touch targets are at least 44x44px
11. Use reduced motion media query for animations
12. Test with screen readers (VoiceOver, NVDA)
13. Use focus trapping in modals
14. New WCAG 2.2: Focus Not Obscured, Dragging Movements""",
            examples=[
                "// Accessible button\n<button\n  onClick={handleClick}\n  aria-pressed={isActive}\n  aria-label=\"Toggle menu\"\n  className=\"focus:ring-2 focus:ring-blue-500 focus:outline-none\"\n>\n  <MenuIcon aria-hidden=\"true\" />\n</button>",
                "// Skip link\n<a href=\"#main-content\" className=\"sr-only focus:not-sr-only\">\n  Skip to main content\n</a>",
                "// Reduced motion\n@media (prefers-reduced-motion: reduce) {\n  *, *::before, *::after {\n    animation-duration: 0.01ms !important;\n    transition-duration: 0.01ms !important;\n  }\n}",
            ],
            priority=10,
            tags=["accessibility", "a11y", "wcag", "aria"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="css",
            topic="Modern CSS Features",
            content="""Modern CSS Best Practices:
1. Use CSS custom properties (variables) for theming
2. Use :has() for parent selection (game changer!)
3. Use container queries for component-responsive design
4. Use CSS nesting (native, no preprocessor needed)
5. Use logical properties: margin-inline, padding-block
6. Use clamp() for fluid typography: clamp(1rem, 2vw, 2rem)
7. Use aspect-ratio for maintaining proportions
8. Use scroll-snap for carousels
9. Use :focus-visible instead of :focus for cleaner focus
10. Use @layer for cascade control
11. Use :where() for zero-specificity selectors
12. Use color-scheme for dark mode
13. Use @supports for progressive enhancement""",
            examples=[
                "/* Container queries */\n.card {\n  container-type: inline-size;\n}\n\n@container (min-width: 400px) {\n  .card-content { display: flex; gap: 1rem; }\n}",
                "/* Parent selection with :has() */\n.form-group:has(:invalid) { border-color: red; }\n.nav:has(.dropdown:hover) { background: rgba(0,0,0,0.1); }",
                "/* CSS nesting */\n.card {\n  padding: 1rem;\n  \n  & .title { font-size: 1.5rem; }\n  \n  &:hover {\n    transform: translateY(-2px);\n    & .title { color: blue; }\n  }\n}",
                "/* Fluid typography */\nh1 { font-size: clamp(1.5rem, 4vw + 1rem, 3rem); }",
            ],
            priority=8,
            tags=["css", "modern-css", "container-queries", "has-selector"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="build",
            topic="Modern Build Tools",
            content="""Modern Build Tools Best Practices:
1. Use Vite for most projects - fast HMR, native ESM
2. Use Turbopack with Next.js for faster dev builds
3. Use Bun as a faster npm alternative
4. Use pnpm for efficient disk usage and speed
5. Use Biome as a faster ESLint + Prettier alternative
6. Use SWC for faster TypeScript compilation
7. Use esbuild for production bundling when possible
8. Use source maps in dev, disable in prod
9. Use tree shaking - avoid side effects in modules
10. Use dynamic imports for code splitting
11. Use bundle analyzer to identify bloat
12. Cache node_modules in CI for faster builds
13. Use parallel builds with Turborepo for monorepos""",
            examples=[
                "// Vite config\nimport { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react-swc';\n\nexport default defineConfig({\n  plugins: [react()],\n  build: { sourcemap: false, minify: 'esbuild' },\n});",
                "// Turbopack with Next.js\nnext dev --turbo",
                "// pnpm workspace for monorepo\npackages:\n  - 'apps/*'\n  - 'packages/*'",
            ],
            priority=8,
            tags=["build", "vite", "turbopack", "bun", "pnpm"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="testing",
            topic="Frontend Testing",
            content="""Frontend Testing Best Practices:
1. Use Vitest for unit/integration tests (fast, Vite-native)
2. Use Testing Library for component tests (user-centric)
3. Use Playwright for E2E tests (cross-browser, fast)
4. Test behavior, not implementation details
5. Use userEvent over fireEvent for realistic interactions
6. Use screen queries: getByRole, getByLabelText (accessible)
7. Avoid getByTestId when possible - prefer accessible queries
8. Use MSW for API mocking
9. Test loading, error, and empty states
10. Use visual regression tests for UI consistency
11. Run tests in CI with coverage reports
12. Use fixtures for test data""",
            examples=[
                "// Component test with Testing Library\nimport { render, screen } from '@testing-library/react';\nimport userEvent from '@testing-library/user-event';\n\ntest('submits form with user data', async () => {\n  const user = userEvent.setup();\n  render(<LoginForm onSubmit={mockSubmit} />);\n  \n  await user.type(screen.getByLabelText('Email'), 'test@test.com');\n  await user.type(screen.getByLabelText('Password'), 'password');\n  await user.click(screen.getByRole('button', { name: 'Sign In' }));\n  \n  expect(mockSubmit).toHaveBeenCalledWith({\n    email: 'test@test.com',\n    password: 'password',\n  });\n});",
                "// E2E with Playwright\ntest('user can complete checkout', async ({ page }) => {\n  await page.goto('/products');\n  await page.click('text=Add to Cart');\n  await page.click('text=Checkout');\n  await page.fill('[name=email]', 'test@test.com');\n  await page.click('text=Place Order');\n  await expect(page.locator('text=Order Confirmed')).toBeVisible();\n});",
            ],
            priority=9,
            tags=["testing", "vitest", "playwright", "testing-library"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="astro",
            topic="Astro Framework",
            content="""Astro Best Practices:
1. Use Astro for content-focused sites (blogs, docs, marketing)
2. Ship zero JavaScript by default - only hydrate what's needed
3. Use partial hydration: client:load, client:visible, client:idle
4. Use any framework: React, Vue, Svelte, Solid
5. Use Content Collections for type-safe markdown/MDX
6. Use View Transitions API for smooth page transitions
7. Use Astro Islands for interactive components
8. Use getStaticPaths for dynamic routes
9. Use Server Islands for personalized content
10. Use Astro DB for SQLite with Turso
11. Use middleware for auth, redirects, headers
12. Built-in image optimization with <Image />""",
            examples=[
                "---\n// Astro component\nimport Card from '../components/Card.astro';\nimport ReactCounter from '../components/Counter.tsx';\n\nconst posts = await getCollection('blog');\n---\n\n{posts.map(post => <Card title={post.data.title} />)}\n\n<!-- Only hydrates when visible -->\n<ReactCounter client:visible />",
                "// Content collection schema\nimport { defineCollection, z } from 'astro:content';\n\nconst blog = defineCollection({\n  type: 'content',\n  schema: z.object({\n    title: z.string(),\n    pubDate: z.date(),\n    tags: z.array(z.string()),\n  }),\n});",
            ],
            priority=8,
            tags=["astro", "islands", "content", "static"]
        ))

        self._add_knowledge(KnowledgeEntry(
            domain="shadcn",
            topic="shadcn/ui Components",
            content="""shadcn/ui Best Practices:
1. Not a component library - copy/paste components you own
2. Built on Radix UI primitives - fully accessible
3. Styled with Tailwind CSS - easy to customize
4. Use 'npx shadcn@latest add <component>' to add
5. Customize in components/ui/ - you own the code
6. Use cn() helper for conditional classes
7. Configure theme in globals.css with CSS variables
8. Works with any React framework (Next.js, Remix, Vite)
9. Components are unstyled by default - add your theme
10. Use the CLI to update components when needed
11. Great for design systems - extend as needed
12. TypeScript-first with full type safety""",
            examples=[
                "// Using shadcn Button\nimport { Button } from '@/components/ui/button';\n\n<Button variant=\"destructive\" size=\"lg\" disabled={isLoading}>\n  {isLoading ? 'Deleting...' : 'Delete Account'}\n</Button>",
                "// Custom variant with cn()\nimport { cn } from '@/lib/utils';\n\nfunction GhostButton({ className, ...props }) {\n  return (\n    <Button\n      className={cn('hover:bg-transparent hover:underline', className)}\n      variant=\"ghost\"\n      {...props}\n    />\n  );\n}",
                "// Theme CSS variables\n:root {\n  --background: 0 0% 100%;\n  --foreground: 222.2 84% 4.9%;\n  --primary: 222.2 47.4% 11.2%;\n}\n\n.dark {\n  --background: 222.2 84% 4.9%;\n  --foreground: 210 40% 98%;\n}",
            ],
            priority=9,
            tags=["shadcn", "radix", "components", "tailwind"]
        ))

    def _add_knowledge(self, entry: KnowledgeEntry):
        """Add a knowledge entry"""
        if entry.domain not in self._knowledge:
            self._knowledge[entry.domain] = []
        self._knowledge[entry.domain].append(entry)

    def _load_tool_documentation(self):
        """Load documentation for available tools"""

        self._tool_docs["filesystem"] = """
FILESYSTEM TOOL:
- read(path): Read file contents
- write(path, content): Write content to file
- append(path, content): Append to file
- list(path, pattern): List files matching pattern
- search(path, pattern, content): Search for content in files
- exists(path): Check if path exists
- info(path): Get file metadata
- delete(path): Delete file (requires permission)
- mkdir(path): Create directory
- execute(path): Execute script (requires permission)
"""

        self._tool_docs["shell"] = """
SHELL TOOL:
- run(command): Execute shell command (requires permission)
- run_safe(command): Execute pre-approved safe commands
- background(command): Run command in background
- env(name): Get environment variable
- set_env(name, value): Set environment variable
- which(command): Find command path
- processes(): List running processes
- kill(pid): Kill process (requires permission)
"""

        self._tool_docs["git"] = """
GIT TOOL:
- status(): Show repository status
- log(limit): Show commit history
- diff(file): Show file changes
- branch(name): Create/list branches
- checkout(branch): Switch branches
- add(files): Stage files
- commit(message): Create commit
- push(remote, branch): Push changes (requires permission)
- pull(remote, branch): Pull changes
- fetch(remote): Fetch from remote
- merge(branch): Merge branch
- stash(action): Manage stash
- init(path): Initialize repository
- clone(url, path): Clone repository
"""

        self._tool_docs["docker"] = """
DOCKER TOOL:
- build(tag, dockerfile, context): Build image
- pull(image): Pull image from registry
- push(image): Push image to registry
- images(): List images
- rmi(image): Remove image
- run(image, name, ports, volumes, env): Run container
- start(container): Start stopped container
- stop(container): Stop running container
- restart(container): Restart container
- rm(container): Remove container
- ps(): List containers
- logs(container, tail): View container logs
- exec(container, command): Execute command in container
- compose_up(services, detach): Start compose services
- compose_down(): Stop compose services
"""

        self._tool_docs["database"] = """
DATABASE TOOL:
- firestore_get(collection, doc_id): Get Firestore document
- firestore_set(collection, doc_id, data): Set document
- firestore_update(collection, doc_id, data): Update document
- firestore_delete(collection, doc_id): Delete document
- firestore_query(collection, where, order_by, limit): Query collection
- firestore_list(): List collections
- sqlite_query(database, query, params): Execute SQLite query
- sqlite_execute(database, statement, params): Execute statement
- sqlite_schema(database): Get database schema
- postgres_query(query, database, host, port, user): PostgreSQL query
- design_schema(description, database_type): Design schema
- generate_migration(from_schema, to_schema): Generate migration
"""

        self._tool_docs["package"] = """
PACKAGE TOOL:
- npm_install(packages, dev): Install npm packages
- npm_run(script): Run npm script
- npm_list(): List installed packages
- pip_install(packages): Install Python packages
- pip_list(): List installed packages
- pip_freeze(): Export requirements
- cargo_build(): Build Rust project
- cargo_test(): Run Rust tests
- brew_install(packages): Install Homebrew packages
- init_project(name, template): Initialize new project
  Templates: react, next, fastapi, flask, fullstack
"""

        self._tool_docs["deploy"] = """
DEPLOY TOOL:
- firebase_deploy(only): Deploy to Firebase
- firebase_hosting(): Deploy hosting only
- firebase_functions(): Deploy functions only
- gcp_run_deploy(service, image, region): Deploy to Cloud Run
- gcp_build(tag): Build with Cloud Build
- vercel_deploy(): Deploy to Vercel
- vercel_preview(): Deploy preview
- aws_lambda_deploy(function, handler): Deploy Lambda
- aws_s3_sync(source, bucket): Sync to S3
- status(service): Get deployment status
- logs(service, lines): View deployment logs
- rollback(service, version): Rollback deployment
"""

        self._tool_docs["frontend"] = """
FRONTEND TOOL:
Package Managers:
- pnpm_install(): Install with pnpm
- pnpm_add(packages, dev): Add packages
- yarn_install(): Install with yarn
- bun_install(): Install with bun
- bun_run(script): Run bun script

Build Tools:
- vite_dev(port): Start Vite dev server
- vite_build(): Build with Vite
- next_dev(port): Start Next.js dev server
- next_build(): Build Next.js app
- turbo_run(task): Run Turborepo task

Linting & Formatting:
- eslint(path): Run ESLint
- eslint_fix(path): ESLint with auto-fix
- prettier(path): Check Prettier
- prettier_write(path): Format with Prettier
- biome_check(path): Run Biome check
- tsc(no_emit): TypeScript compiler

Testing:
- vitest(): Run Vitest tests
- vitest_coverage(): With coverage
- playwright_test(headed, project): E2E tests
- cypress_run(spec): Run Cypress

Tailwind CSS:
- tailwind_init(full): Initialize Tailwind
- tailwind_build(input, output, minify): Build
- tailwind_watch(input, output): Watch mode

Component Scaffolding:
- create_component(name, framework, typescript): Create component
- create_page(name, framework): Create page
- create_hook(name): Create React hook
- create_store(name, library): Create Zustand/Pinia store
- create_api_route(name, method): Create API route

Storybook:
- storybook_dev(port): Start Storybook
- storybook_build(): Build Storybook
- create_story(component): Create story

Analysis:
- analyze_bundle(): Bundle size analysis
- lighthouse(url): Lighthouse audit
- check_deps(): Check dependencies
- find_unused(): Find unused deps

Project Creation:
- create_next_app(name, ts, tailwind): New Next.js
- create_vite_app(name, template): New Vite
- create_astro_app(name, template): New Astro
- create_remix_app(name): New Remix
"""

    def get_system_prompt(
        self,
        task_type: str = "general",
        domains: Optional[List[str]] = None,
        include_tools: bool = True,
        project_context: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive system prompt for Ollama models.

        Args:
            task_type: Type of task (coding, debugging, architecture, etc.)
            domains: Specific domains to include knowledge for
            include_tools: Whether to include tool documentation
            project_context: Additional project-specific context

        Returns:
            Complete system prompt with injected knowledge
        """
        parts = []

        # Core identity
        parts.append("""You are an expert AI developer assistant, part of the El Gringo Development Team.
You have deep expertise in software development and can help with coding, debugging,
architecture, and deployment tasks. You work collaboratively with other AI models
(Claude, ChatGPT, Gemini, Grok) to deliver the best solutions.

IMPORTANT PRINCIPLES:
1. Write clean, maintainable, well-documented code
2. Follow best practices for the language/framework being used
3. Consider security implications of all code
4. Handle errors gracefully with proper logging
5. Test your code mentally before suggesting it
6. If unsure, ask for clarification rather than guessing""")

        # Add domain-specific knowledge
        if domains:
            parts.append("\n\n## DOMAIN EXPERTISE\n")
            for domain in domains:
                if domain in self._knowledge:
                    for entry in sorted(self._knowledge[domain], key=lambda x: -x.priority):
                        parts.append(f"\n### {entry.topic}\n{entry.content}")
                        if entry.examples:
                            parts.append("\nExamples:")
                            for ex in entry.examples[:2]:
                                parts.append(f"```\n{ex}\n```")

        # Add tool documentation
        if include_tools:
            parts.append("\n\n## AVAILABLE TOOLS\n")
            parts.append("You can use these tools to help complete tasks:\n")
            for tool_name, doc in self._tool_docs.items():
                parts.append(f"\n{doc}")

            parts.append("""
To use a tool, format your request as:
TOOL_CALL: tool_name.operation(param1="value1", param2="value2")

Example:
TOOL_CALL: filesystem.read(path="./src/main.py")
TOOL_CALL: git.status()
TOOL_CALL: shell.run_safe(command="python -m pytest tests/")
""")

        # Add project context
        if project_context:
            parts.append(f"\n\n## PROJECT CONTEXT\n{project_context}")

        # Add task-specific guidance
        task_guidance = {
            "coding": """
## CODING TASK GUIDANCE
- Write production-ready code
- Include type hints (Python) or types (TypeScript)
- Add docstrings/comments for complex logic
- Handle edge cases and errors
- Consider performance implications""",

            "debugging": """
## DEBUGGING TASK GUIDANCE
- Analyze the error message carefully
- Identify the root cause, not just symptoms
- Check for common issues (null values, type errors, async issues)
- Suggest fixes with explanations
- Recommend prevention strategies""",

            "architecture": """
## ARCHITECTURE TASK GUIDANCE
- Consider scalability and maintainability
- Follow SOLID principles
- Use appropriate design patterns
- Plan for error handling and recovery
- Document trade-offs in decisions""",

            "security": """
## SECURITY TASK GUIDANCE
- Never suggest storing secrets in code
- Validate all user inputs
- Use parameterized queries for databases
- Implement proper authentication/authorization
- Log security events for monitoring"""
        }

        if task_type in task_guidance:
            parts.append(task_guidance[task_type])

        return "\n".join(parts)

    def get_knowledge_for_topic(self, topic: str) -> List[KnowledgeEntry]:
        """Get all knowledge entries related to a topic"""
        results = []
        topic_lower = topic.lower()

        for domain, entries in self._knowledge.items():
            for entry in entries:
                if (topic_lower in entry.topic.lower() or
                    topic_lower in entry.content.lower() or
                    any(topic_lower in tag for tag in entry.tags)):
                    results.append(entry)

        return sorted(results, key=lambda x: -x.priority)

    def add_project_knowledge(self, domain: str, topic: str, content: str, examples: List[str] = None):
        """Add project-specific knowledge"""
        self._add_knowledge(KnowledgeEntry(
            domain=domain,
            topic=f"[Project] {topic}",
            content=content,
            examples=examples or [],
            priority=10,  # High priority for project-specific knowledge
            tags=["project", domain]
        ))

    def get_tool_doc(self, tool_name: str) -> str:
        """Get documentation for a specific tool"""
        return self._tool_docs.get(tool_name, f"No documentation available for {tool_name}")

    def export_knowledge(self, path: str):
        """Export knowledge base to JSON file"""
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "knowledge": {
                domain: [
                    {
                        "topic": e.topic,
                        "content": e.content,
                        "examples": e.examples,
                        "priority": e.priority,
                        "tags": e.tags
                    }
                    for e in entries
                ]
                for domain, entries in self._knowledge.items()
            },
            "tool_docs": self._tool_docs
        }

        with open(path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported knowledge base to {path}")

    def import_knowledge(self, path: str):
        """Import knowledge from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)

        for domain, entries in data.get("knowledge", {}).items():
            for entry_data in entries:
                self._add_knowledge(KnowledgeEntry(
                    domain=domain,
                    **entry_data
                ))

        self._tool_docs.update(data.get("tool_docs", {}))
        logger.info(f"Imported knowledge from {path}")


# Global knowledge base instance
_knowledge_base: Optional[OllamaKnowledgeBase] = None


def get_ollama_knowledge_base(project_path: Optional[str] = None) -> OllamaKnowledgeBase:
    """Get or create the global knowledge base"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = OllamaKnowledgeBase(project_path=project_path)
    return _knowledge_base


def get_enhanced_prompt(
    task: str,
    task_type: str = "general",
    domains: Optional[List[str]] = None,
    include_tools: bool = True,
    project_context: Optional[str] = None
) -> str:
    """
    Get an enhanced prompt with knowledge injection for Ollama.

    Args:
        task: The task description
        task_type: Type of task
        domains: Relevant domains
        include_tools: Include tool documentation
        project_context: Project-specific context

    Returns:
        Enhanced prompt with system context
    """
    kb = get_ollama_knowledge_base()
    system_prompt = kb.get_system_prompt(
        task_type=task_type,
        domains=domains,
        include_tools=include_tools,
        project_context=project_context
    )

    return f"{system_prompt}\n\n## CURRENT TASK\n{task}"
