# Full-Stack CRUD Application Template

A complete, production-ready CRUD application with:
- **Backend**: FastAPI + SQLAlchemy + JWT Auth
- **Frontend**: Next.js + React + Tailwind CSS
- **Database**: PostgreSQL (or SQLite for development)

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
crud_app/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Configuration
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API routes
│   ├── services/            # Business logic
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   ├── lib/                 # Utilities & API client
│   └── package.json
└── docker-compose.yml
```

## Features

### Backend
- JWT authentication with refresh tokens
- Role-based access control
- Request validation with Pydantic
- Database migrations with Alembic
- Async SQLAlchemy
- Health checks
- CORS configuration

### Frontend
- Server-side rendering with Next.js 14
- Form handling with react-hook-form + zod
- Data tables with sorting, filtering, pagination
- Dashboard layout with responsive sidebar
- Toast notifications
- Loading states & error handling
- Dark mode support

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new user |
| POST | /auth/login | Login and get tokens |
| POST | /auth/refresh | Refresh access token |
| GET | /auth/me | Get current user |
| GET | /items | List items |
| POST | /items | Create item |
| GET | /items/{id} | Get item |
| PUT | /items/{id} | Update item |
| DELETE | /items/{id} | Delete item |

## Customization

1. **Change the model**: Edit `backend/models/item.py` and `backend/schemas/item.py`
2. **Add new routes**: Create new router in `backend/routers/`
3. **Modify UI**: Edit components in `frontend/components/`
4. **Change styling**: Edit `frontend/tailwind.config.js`

## Deployment

### Docker
```bash
docker-compose up -d
```

### Manual
- Deploy backend to Railway, Render, or any Python host
- Deploy frontend to Vercel, Netlify, or similar
- Set up PostgreSQL database

## License

MIT - Use freely for any project.
