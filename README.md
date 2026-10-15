# ALABATT-HUB

A full-stack system for a Centre for Sport Unit, covering both the backend API and the frontend experience for members, staff, coaches, and managers.

## Project Vision

ALABATT-HUB is designed to manage the day-to-day operations of a sports centre, including:

- membership registration and lifecycle management
- user authentication and role-based access
- sports centre and facility administration
- booking requests and approvals
- equipment lending and inventory tracking
- payments, refunds, and notifications
- dashboard reporting for managers and administrators

The project is intentionally structured so the backend exposes reusable API services, while the frontend consumes those APIs to deliver a usable application experience.

## Full-Stack Architecture

### Frontend layer

The project includes a dedicated frontend folder intended for the client-side application, which will handle:

- member dashboard views
- membership plans and sign-up
- facility and booking screens
- admin reporting and management dashboards
- notification displays
- staff and finance workflows

### Backend layer

The backend is built with Django and Django REST Framework and is responsible for:

- business logic and validation
- secure authentication with JWT
- database persistence and API endpoints
- domain models for sports centre operations
- reporting and analytics data

### Shared flow

```text
Frontend UI
   ↓
HTTP requests to Django REST API
   ↓
Authentication + business rules
   ↓
PostgreSQL database
   ↓
JSON responses to frontend
```

## Tech Stack

### Backend

- Python
- Django 5.2
- Django REST Framework
- PostgreSQL
- django-cors-headers
- djangorestframework-simplejwt
- python-dotenv

### Frontend

- planned for a modern client framework such as React or Next.js
- connected through REST API endpoints
- designed to consume JWT tokens for protected access

## Current Project Structure

```text
ALABATT-HUB/
├── backend/
│   ├── accounts/
│   ├── bookings/
│   ├── config/
│   ├── equipment/
│   ├── memberships/
│   ├── notifications/
│   ├── payments/
│   ├── reports/
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3
│   ├── venv/
│   └── .env
├── frontend/
│   └── (frontend app to be created / connected)
├── docs/
│   ├── ClassDiagram.png
│   └── UseCaseDiagram1.png
├── README.md
└── .gitignore
```

## Current Backend Features

The backend already includes domain models and API modules for:

- `User`
- `MembershipType`
- `Membership`
- `SportsCentre`
- `Facility`
- `Booking`
- `Equipment`
- `EquipmentLoan`
- `Payment`
- `Refund`
- `Notification`

## API Overview

### Authentication and JWT

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `GET /api/auth/me/`

### Memberships

- `GET /api/membership-types/`
- `POST /api/membership-types/`
- `GET /api/membership-types/<id>/`
- `PUT /api/membership-types/<id>/`
- `DELETE /api/membership-types/<id>/`
- `GET /api/memberships/`
- `POST /api/memberships/`
- `GET /api/memberships/<id>/`
- `PUT /api/memberships/<id>/`
- `DELETE /api/memberships/<id>/`

### Bookings and Centres

- `GET /api/centres/`
- `POST /api/centres/`
- `GET /api/centres/<id>/`
- `PUT /api/centres/<id>/`
- `DELETE /api/centres/<id>/`
- `GET /api/facilities/`
- `POST /api/facilities/`
- `GET /api/facilities/<id>/`
- `PUT /api/facilities/<id>/`
- `DELETE /api/facilities/<id>/`
- `GET /api/bookings/`
- `POST /api/bookings/`
- `GET /api/bookings/<id>/`
- `PUT /api/bookings/<id>/`
- `DELETE /api/bookings/<id>/`

### Equipment

- `GET /api/equipment/`
- `POST /api/equipment/`
- `GET /api/equipment/<id>/`
- `PUT /api/equipment/<id>/`
- `DELETE /api/equipment/<id>/`
- `GET /api/equipment-loans/`
- `POST /api/equipment-loans/`
- `GET /api/equipment-loans/<id>/`
- `PUT /api/equipment-loans/<id>/`
- `DELETE /api/equipment-loans/<id>/`

### Payments and Refunds

- `GET /api/payments/`
- `POST /api/payments/`
- `GET /api/payments/<id>/`
- `PUT /api/payments/<id>/`
- `DELETE /api/payments/<id>/`
- `GET /api/refunds/`
- `POST /api/refunds/`
- `GET /api/refunds/<id>/`
- `PUT /api/refunds/<id>/`
- `DELETE /api/refunds/<id>/`

### Notifications

- `GET /api/notifications/`
- `POST /api/notifications/`
- `GET /api/notifications/<id>/`
- `PUT /api/notifications/<id>/`
- `DELETE /api/notifications/<id>/`

### Reports

- `GET /api/reports/overview/`

## Frontend Use Cases

The frontend should support the main user journeys of the sports centre system:

- member sign-up and login
- viewing membership plans
- booking a facility
- checking booking status
- submitting equipment loan requests
- viewing notifications
- viewing manager dashboard summaries and revenue metrics

## Setup

### Backend

1. Open the backend folder.
2. Activate the virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the API:

```bash
python manage.py migrate
python manage.py runserver
```

### Frontend

1. Create or connect the frontend app under the root `frontend/` folder.
2. Point the frontend to the backend API base URL.
3. Use JWT tokens for authenticated requests.

## Design Artifacts

The repository includes system modeling documents in the `docs/` folder, including:

- use case diagram
- class diagram

These diagrams provide the project’s functional and object-oriented design basis.

## Notes

This repository is evolving as a full-stack sports-centre platform, where the backend provides the domain logic and APIs while the frontend delivers the actual user experience. The current focus is a robust Django API foundation that can power the eventual web application interface.
