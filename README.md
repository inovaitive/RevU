# RevU - AI Product Feedback Reviewer Tool

> Transform customer feedback into actionable insights with AI-powered analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)

## 🎯 Overview

**RevU** is an intelligent B2B SaaS platform that analyzes product feedback and reviews using AI to help product teams make data-driven decisions. By leveraging Claude 3.5 Sonnet and advanced NLP techniques, RevU automatically categorizes feedback, extracts sentiment, identifies themes, and surfaces actionable insights like churn risks and competitive intelligence.

### Key Problems We Solve

- **Feedback Overload**: Product teams drowning in reviews from multiple sources (G2, Capterra, support tickets, surveys)
- **Manual Triage**: Hours spent manually categorizing and prioritizing customer feedback
- **Hidden Insights**: Critical signals (churn risk, competitor mentions, feature gaps) buried in unstructured text
- **Delayed Action**: Slow response to urgent customer issues due to information scatter

### Who Is This For?

- **Product Managers**: Prioritize roadmap based on real customer needs
- **Customer Success Teams**: Identify churn risks early and act proactively
- **Support Teams**: Triage issues faster with automatic categorization
- **Executives**: Track product health and customer sentiment trends
- **Sales Teams**: Leverage competitive intelligence from customer feedback

---

## ✨ Key Features

### Core Capabilities

- **🤖 AI-Powered Analysis**
  - Sentiment analysis (positive, negative, neutral, mixed)
  - Automatic categorization (bug reports, feature requests, complaints, praise)
  - Theme extraction (UI, performance, integrations, support quality)
  - Entity recognition (competitor mentions, product features, user roles)

- **📊 Intelligent Prioritization**
  - Priority scoring based on urgency, impact, and business relevance
  - Churn risk detection from language patterns
  - Competitive intelligence extraction
  - Feature demand quantification

- **🔍 Multi-Source Ingestion**
  - CSV upload for historical data
  - Manual entry via web form
  - Integration with G2, Capterra, ProductHunt (automated scraping)
  - Future: Intercom, Zendesk, custom APIs

- **👥 Human-in-the-Loop (HITL)**
  - AI flags low-confidence or high-impact cases for review
  - Validation workflow to improve accuracy over time
  - Feedback loop for continuous model improvement

- **📈 Interactive Dashboard**
  - Sentiment trends over time
  - Top themes and keywords
  - Urgent issues requiring attention
  - Churn risk alerts
  - Competitive mentions tracker

- **📄 Reports & Exports**
  - Executive summaries
  - Weekly/monthly digests
  - Custom date range reports
  - Export to CSV, PDF
  - Scheduled email delivery

- **🔐 Enterprise-Ready**
  - Multi-tenant architecture
  - Role-based access control (RBAC)
  - Secure authentication (JWT)
  - Data privacy compliance (GDPR-ready)

---

## 🏗️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance async Python web framework
- **Database**: [PostgreSQL 15+](https://www.postgresql.org/) - Primary data store
- **Cache/Queue**: [Redis 7+](https://redis.io/) - Session cache and Celery message broker
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) - Database abstraction layer
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/) - Database schema versioning
- **Task Queue**: [Celery](https://docs.celeryq.dev/) - Async background job processing

### AI & NLP
- **LLM**: [Anthropic Claude 3.5 Sonnet](https://www.anthropic.com/claude) - Deep semantic analysis, sentiment, insights
- **NLP**: [spaCy](https://spacy.io/) (en_core_web_lg) - Entity extraction, preprocessing, keyword detection
- **Approach**: Hybrid AI pipeline combining rule-based NLP with LLM reasoning

### Frontend
- **Framework**: [React 18+](https://reactjs.org/) - Component-based UI
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- **Build Tool**: [Vite](https://vitejs.dev/) - Fast dev server and optimized builds
- **State Management**: React Query + Context API
- **Charts**: Recharts or Chart.js - Data visualization
- **Forms**: React Hook Form - Efficient form handling

### Web Scraping
- **Dynamic Pages**: [Playwright](https://playwright.dev/) - Headless browser automation
- **HTML Parsing**: [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML extraction

### DevOps & Deployment
- **Containerization**: Docker + Docker Compose
- **Hosting**: Railway (primary) or AWS ECS
- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry (error tracking), structured logging

---

## 📂 Project Structure

```
RevU/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API routes (v1)
│   │   │   └── v1/
│   │   │       ├── feedback.py
│   │   │       ├── analysis.py
│   │   │       ├── reports.py
│   │   │       ├── integrations.py
│   │   │       └── auth.py
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic layer
│   │   │   ├── ai_analyzer.py
│   │   │   ├── sentiment.py
│   │   │   ├── categorizer.py
│   │   │   ├── prioritizer.py
│   │   │   └── insights.py
│   │   ├── integrations/      # External platform connectors
│   │   │   ├── g2.py
│   │   │   ├── capterra.py
│   │   │   └── slack.py
│   │   ├── tasks/             # Celery async tasks
│   │   ├── scrapers/          # Web scraping logic
│   │   ├── utils/             # Helper utilities
│   │   ├── middleware/        # Auth, RBAC, CORS
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # DB connection setup
│   │   └── main.py            # FastAPI app entry point
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # React frontend application
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/        # Reusable UI components
│   │   │   ├── dashboard/     # Dashboard widgets
│   │   │   ├── feedback/      # Feedback management
│   │   │   ├── reports/       # Report views
│   │   │   └── admin/         # Admin panels
│   │   ├── pages/             # Route pages
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API client
│   │   ├── utils/             # Helper functions
│   │   └── App.jsx
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml          # Local development environment
├── .env.example                # Environment variables template
├── .gitignore
├── LICENSE
├── README.md                   # This file
└── ROADMAP.md                  # Development roadmap
```

---

## 🚀 Getting Started

### Prerequisites

- **Docker** & **Docker Compose** (recommended for easiest setup)
- **OR** Manual setup:
  - Python 3.11+
  - Node.js 18+
  - PostgreSQL 15+
  - Redis 7+

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/inovaitive/RevU.git
cd RevU

# 2. Copy environment variables
cp .env.example .env

# 3. Edit .env and add your API keys
# - ANTHROPIC_API_KEY=your_claude_api_key
# - DATABASE_URL, REDIS_URL (defaults work for Docker)

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Access the application
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Manual Setup (Development)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../.env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Background Workers (Celery)

```bash
cd backend

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```bash
# Application
APP_NAME=RevU
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://revu_user:revu_pass@localhost:5432/revu_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
ANTHROPIC_API_KEY=your_claude_api_key_here

# Authentication
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External Integrations (optional)
SLACK_WEBHOOK_URL=
SENDGRID_API_KEY=

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📖 API Documentation

Once the backend is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core API Endpoints

#### Authentication
```
POST   /api/v1/auth/register       # Create new user
POST   /api/v1/auth/login          # Login and get JWT token
GET    /api/v1/auth/me             # Get current user info
```

#### Feedback
```
GET    /api/v1/feedback            # List all feedback (with filters)
POST   /api/v1/feedback            # Create new feedback entry
GET    /api/v1/feedback/{id}       # Get single feedback detail
PUT    /api/v1/feedback/{id}       # Update feedback
DELETE /api/v1/feedback/{id}       # Delete feedback
POST   /api/v1/feedback/batch      # Bulk upload (CSV)
```

#### Analysis
```
POST   /api/v1/analysis/trigger    # Trigger AI analysis
GET    /api/v1/analysis/{id}       # Get analysis results
PUT    /api/v1/analysis/{id}/review # Human review (HITL)
```

#### Dashboard
```
GET    /api/v1/dashboard/stats               # Overall metrics
GET    /api/v1/dashboard/sentiment-trend     # Sentiment over time
GET    /api/v1/dashboard/top-themes          # Most mentioned themes
GET    /api/v1/dashboard/urgent-items        # High priority items
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_analysis.py
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

---

## 🛠️ Development Guidelines

### Code Style

- **Backend**: Follow PEP 8, use `black` for formatting, `flake8` for linting
- **Frontend**: ESLint + Prettier configuration
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/)

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, commit
git add .
git commit -m "feat: add sentiment analysis visualization"

# Push to remote
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

### Database Migrations

```bash
# Create new migration after model changes
alembic revision --autogenerate -m "Add analysis table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## 🗺️ Roadmap

See [ROADMAP.md](./ROADMAP.md) for detailed development plan.

**Current Phase**: Foundation & MVP (Weeks 1-2)

**Upcoming Milestones**:
- ✅ Project setup and architecture
- 🚧 Core feedback analysis with Claude
- 📅 Dashboard and visualization
- 📅 G2/Capterra integrations
- 📅 HITL review workflow
- 📅 Multi-tenancy and RBAC

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Anthropic** for Claude 3.5 Sonnet API
- **FastAPI** for the excellent Python web framework
- **spaCy** for industrial-strength NLP
- Open source community for amazing tools

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/inovaitive/RevU/issues)
- **Discussions**: [GitHub Discussions](https://github.com/inovaitive/RevU/discussions)

---

## 🎯 Success Metrics

We're tracking these KPIs to measure RevU's effectiveness:

- **Analysis Accuracy**: >85% sentiment accuracy (validated by HITL)
- **Processing Speed**: <5 seconds per feedback item
- **HITL Rate**: <15% items requiring human review
- **User Satisfaction**: Net Promoter Score (NPS) tracking
- **Platform Uptime**: 99.5% availability

---

**Built with ❤️ for product teams who want to truly listen to their customers**
