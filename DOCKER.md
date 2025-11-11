# Docker Setup Guide for ProGestock

This guide explains how to run the ProGestock application using Docker and Docker Compose.

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** (included with Docker Desktop)
- Git (optional, for cloning the repository)

### Install Docker

- **Windows/Mac**: Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: Follow the [official installation guide](https://docs.docker.com/engine/install/)

Verify installation:
```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone the Repository (if not already done)

```bash
git clone <repository-url>
cd ProGestock
```

### 2. Configure Environment Variables

Copy the example environment file and update it with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `SECRET_KEY`: Generate a new Django secret key
- `GOOGLE_OAUTH_CLIENT_ID`: Your Google OAuth credentials
- `GOOGLE_OAUTH_CLIENT_SECRET`: Your Google OAuth secret
- `EMAIL_HOST_USER`: Your email address
- `EMAIL_HOST_PASSWORD`: Your email app password
- `GEMINI_API_KEY`: (Optional) Google Gemini API key

**Important**: For Docker, ensure these are set correctly in `.env`:
```env
DATABASE_URL=postgres://progestock_user:your-password@db:5432/progestock_db
CELERY_BROKER_URL=redis://redis:6379/0
```

### 3. Build and Start All Services

This single command will start Django, Celery, PostgreSQL, and Redis:

```bash
docker-compose up -d
```

The `-d` flag runs containers in the background (detached mode).

### 4. Run Database Migrations

```bash
docker-compose exec web python manage.py migrate
```

### 5. Create a Superuser (Optional)

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Access the Application

- **Django API**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Docker Services Overview

Your application runs as multiple interconnected services:

| Service | Description | Port |
|---------|-------------|------|
| **web** | Django REST API server | 8000 |
| **celery_worker** | Async task processor (emails, etc.) | - |
| **db** | PostgreSQL database | 5432 |
| **redis** | Cache & Celery message broker | 6379 |

## Common Commands

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
```

### Restart a service
```bash
docker-compose restart web
docker-compose restart celery_worker
```

### Run Django management commands
```bash
# Make migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Access a service shell
```bash
# Django shell
docker-compose exec web python manage.py shell

# Database shell
docker-compose exec web python manage.py dbshell

# PostgreSQL shell
docker-compose exec db psql -U progestock_user -d progestock_db

# Container bash shell
docker-compose exec web bash
```

### Rebuild containers (after dependency changes)
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View running containers
```bash
docker-compose ps
```

### Remove all containers and volumes
```bash
docker-compose down -v
```
**Warning**: This deletes all data in the database!

## Development Workflow

### Code Changes

The `docker-compose.override.yml` file enables hot-reloading:
- Changes to Python files automatically reload Django
- No need to restart containers for code changes

### Updating Dependencies

After modifying `requirements.txt`:
```bash
docker-compose build web celery_worker
docker-compose up -d
```

### Database Management

**Backup database**:
```bash
docker-compose exec db pg_dump -U progestock_user progestock_db > backup.sql
```

**Restore database**:
```bash
docker-compose exec -T db psql -U progestock_user progestock_db < backup.sql
```

**Reset database** (delete all data and start fresh):
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Troubleshooting

### Port already in use

If you see "port is already allocated":
```bash
# Stop the conflicting service or change the port in docker-compose.yml
# For example, change "8000:8000" to "8001:8000"
```

### Database connection errors

```bash
# Check if database is healthy
docker-compose ps

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Celery not processing tasks

```bash
# View Celery logs
docker-compose logs -f celery_worker

# Restart Celery
docker-compose restart celery_worker
```

### Permission errors (Linux/Mac)

If you encounter permission issues:
```bash
# Fix ownership
sudo chown -R $USER:$USER .

# Or run with sudo (not recommended)
sudo docker-compose up -d
```

### Slow performance on Windows

Enable WSL 2 backend in Docker Desktop settings for better performance.

### Clear all Docker resources

```bash
# Stop all containers
docker-compose down

# Remove all unused containers, networks, images
docker system prune -a

# WARNING: This removes ALL Docker data
docker system prune -a --volumes
```

## Production Deployment

For production, you'll need additional configuration:

1. **Create `docker-compose.prod.yml`** with production settings:
   - Use environment variables instead of .env file
   - Set `DEBUG=False`
   - Configure proper SECRET_KEY
   - Use gunicorn instead of runserver
   - Set up nginx for static files
   - Enable HTTPS

2. **Security**:
   - Never commit `.env` to version control
   - Use secrets management (Docker secrets, AWS Secrets Manager, etc.)
   - Set up proper firewall rules
   - Enable SSL/TLS

3. **Scaling**:
   ```bash
   docker-compose up -d --scale celery_worker=3
   ```

4. **Monitoring**:
   - Add health checks
   - Set up logging (ELK stack, CloudWatch, etc.)
   - Monitor container metrics

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                  │
│  (progestock_network)                           │
│                                                  │
│  ┌─────────┐    ┌──────────────┐    ┌────────┐ │
│  │  Redis  │◄───┤ Celery Worker│    │   DB   │ │
│  │  :6379  │    └──────────────┘    │ :5432  │ │
│  └─────────┘            ▲            └────────┘ │
│       ▲                 │                ▲       │
│       │                 │                │       │
│       │          ┌──────┴──────┐        │       │
│       └──────────┤  Django Web │────────┘       │
│                  │   :8000     │                 │
│                  └─────────────┘                 │
│                         │                        │
└─────────────────────────┼────────────────────────┘
                          │
                    (Host: localhost:8000)
```

## Next Steps

Once you have Docker running smoothly in development:

1. **Phase 2**: Add Kubernetes configuration for cloud deployment
2. **Phase 3**: Set up CI/CD pipelines (GitHub Actions, GitLab CI)
3. **Phase 4**: Deploy to cloud (AWS ECS, Google Cloud Run, Azure AKS)

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Docker Best Practices](https://docs.docker.com/samples/django/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
