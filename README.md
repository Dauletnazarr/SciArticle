# SciArticle

SciArticle is a web application designed to help users find and share scientific articles. It includes a Telegram bot that allows users to search for articles by DOI (Digital Object Identifier), request PDFs, and collaborate with other users to validate uploaded articles.

## Features

- **Article Requests**: Users can request articles by providing a DOI
- **PDF Uploads**: Community members can upload PDFs in response to requests
- **Validation System**: Community-based validation of uploaded PDFs
- **Reward System**: Users earn subscription benefits for contributing uploads and validations
- **Telegram Integration**: Access the service directly through a Telegram bot

## Technology Stack

- **Backend**: Django (Python)
- **Task Queue**: Celery with Redis
- **Testing**: pytest
- **Containerization**: Docker and docker-compose
- **Database**: PostgreSQL (implied from Docker setup)

## Project Structure

- **`src/`**: Main application code
  - **`api/`**: API endpoints
  - **`bot/`**: Telegram bot implementation
  - **`common/`**: Shared utilities and components
  - **`sciarticle/`**: Django project settings
- **`tests/`**: Test suite
- **`infra/`**: Infrastructure configuration (Docker, etc.)
- **`data/`**: Data storage
- **`docs/`**: Project documentation

## Setup and Installation

### Prerequisites

- Python 3.12+
- Poetry (Python package manager)
- Docker and docker-compose (for containerized deployment)
- Redis (for Celery task queue)

### Local Development

1. Clone the repository:
```
git clone https://github.com/yourusername/sciarticle.git
   cd sciarticle
```


2. Install dependencies with Poetry:
```
poetry install
```


3. Create a `.env` file based on `.env.example`

4. Run the development server:
```
poetry run python src/manage.py runserver
```


5. Start Celery worker:
```
poetry run celery -A src.celery_app worker -l info
```


### Testing

Run tests with pytest:
```
poetry run pytest
```


Or use the provided script:
```
./run_tests.sh
```


### Docker Deployment

Use docker-compose to build and run the application:
```
docker-compose up -d
```


## Environment Variables

Create a `.env` file in the project root with the following required variables:

```
# Database configuration
POSTGRES_DB=sciarticle
POSTGRES_USER=django
POSTGRES_PASSWORD=your_secure_password
DB_HOST=postgres  # Use 'localhost' for local development without Docker
DB_PORT=5432

# Telegram integration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token  # Get this from @BotFather

# Redis configuration (for Celery)
REDIS_HOST=redis  # Use 'localhost' for local development without Docker
REDIS_PORT=6379

# Django settings
SECRET_KEY=your_django_secret_key  # Or leave empty to auto-generate
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost 127.0.0.1  # Add your domain in production
```


Optional environment variables with their defaults:
```
# Database engine
DB_ENGINE=django.db.backends.postgresql
```


For local development, you can use the `.env.example` file as a template. In a production environment, make sure to:
1. Set `DEBUG=False`
2. Add your domain to `ALLOWED_HOSTS`
3. Use strong, unique passwords
4. Generate a proper `SECRET_KEY` rather than relying on auto-generation

## Configuration

The application uses environment variables for configuration as detailed above. See `.env.example` for more details.

## How It Works

1. Users request articles via the Telegram bot by providing a DOI
2. Community members can upload PDFs to fulfill these requests
3. Other users validate the uploaded PDFs
4. Once validated, the requester receives the PDF
5. Contributors earn rewards based on their participation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Create a pull request

Please follow the project's coding standards and commit message conventions.

## License

This project is licensed under the terms of the LICENSE file included in the repository.