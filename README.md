# Cinema Mate API

Cinema Mate is an asynchronous web service built with **FastAPI** for managing movies, orders, payments, and shopping carts. It provides role-based access, Stripe payment integration, and full test coverage.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [CI/CD](#cicd)

---

## Features

- CRUD operations for movies, orders, and shopping carts
- User authentication and role-based permissions (e.g., moderators)
- Payment handling with **Stripe**
- Asynchronous database operations using **SQLAlchemy Async**
- Unit and integration tests with **pytest** and **pytest-asyncio**
- Dockerized development and production environment
- Pydantic validation with modern V2 syntax

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic V2  
- **Database:** PostgreSQL (async), SQLite (for local dev/testing)  
- **ORM:** SQLAlchemy Async  
- **Payments:** Stripe  
- **Testing:** pytest, pytest-asyncio  
- **CI/CD:** GitHub Actions  
- **Containerization:** Docker  

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<username>/cinema-mate.git
cd cinema-mate

---

## Configuration

Create a .env file in the root directory with the following variables:

- **MODE=DEV
- **DATABASE_URL=postgresql+asyncpg://user:password@localhost/db_name
- **SECRET_KEY=<your_secret_key>
- **STRIPE_SECRET_KEY=<your_stripe_secret_key>
- **AWS_ACCESS_KEY_ID=<aws_key>
- **AWS_SECRET_ACCESS_KEY=<aws_secret>
- **AWS_REGION=<aws_region>

---

## Running the Project
Locally:
- **export MODE=DEV      # Linux/macOS
- **$env:MODE="DEV"      # Windows PowerShell
- **uvicorn src.create_fastapi:app --reload

---

## Docker:
- **docker build -t cinema:latest .
- **docker run -p 8000:8000 cinema:latest

---

## Testing

Run all tests:

- **export MODE=TEST      # Linux/macOS
- **$env:MODE="TEST"      # Windows PowerShell
- **PYTHONPATH=src pytest

---

## API Documentation

Interactive API docs are available at:

Swagger UI: http://127.0.0.1:8000/docs

---

## CI/CD

This project uses GitHub Actions for:

- **Running linters (flake8, black)

- **Running tests (pytest)

- **Building and pushing Docker images to AWS ECR

- **Deploying to AWS ECS



