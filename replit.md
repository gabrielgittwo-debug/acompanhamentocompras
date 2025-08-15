# SENAI Acquisition Management System

## Overview

The SENAI Acquisition Management System is a comprehensive web application designed for SENAI Morvan Figueiredo to manage and track acquisition processes for services and supplies. The system provides complete traceability from initial request through completion, with role-based access control, financial tracking, and automated notifications.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **Styling**: Custom CSS with SENAI institutional branding (blue color scheme)
- **JavaScript**: Vanilla JS with Chart.js for data visualization
- **Component Structure**: Modular template inheritance with base layout

### Backend Architecture
- **Framework**: Flask web framework with blueprints for modular organization
- **Authentication**: Replit Auth integration with OAuth2 flow
- **Authorization**: Role-based access control (Admin, Solicitante, Aprovador, Recebimento)
- **Database ORM**: SQLAlchemy with declarative models
- **File Upload**: Werkzeug secure file handling with 16MB limit

### Data Model
- **Users**: Replit Auth integration with role assignments
- **Acquisitions**: Core entity with type classification (Services/Supplies)
- **Categories**: Hierarchical categorization system
- **Status Tracking**: Workflow states (Em Análise, Aprovado, Em Cotação, etc.)
- **Documents**: File attachment system for supporting documentation
- **Audit Trail**: Complete history tracking for all status changes

### Business Logic
- **Workflow Management**: Status-based approval process with automated transitions
- **Financial Tracking**: Budget source allocation and payment method tracking
- **Notification System**: Email alerts for status changes and approvals
- **Reporting**: PDF and Excel report generation with charts and analytics

### Security & Session Management
- **Authentication**: Mandatory login for all operations
- **Session Management**: Permanent sessions with ProxyFix for HTTPS
- **File Security**: Secure filename handling and upload validation
- **Access Control**: Route-level authorization based on user roles

## External Dependencies

### Third-Party Services
- **Replit Auth**: Primary authentication provider with OAuth2 flow
- **Email Service**: SMTP integration for automated notifications (Gmail/custom SMTP)

### JavaScript Libraries
- **Bootstrap 5**: UI framework for responsive design
- **Font Awesome 6**: Icon library for consistent iconography
- **Chart.js**: Data visualization for dashboards and reports

### Python Packages
- **Flask**: Core web framework
- **SQLAlchemy**: Database ORM and query builder
- **Flask-Login**: Session management and user authentication
- **Flask-Dance**: OAuth integration for Replit Auth
- **ReportLab**: PDF generation for reports
- **OpenPyXL/Pandas**: Excel report generation
- **Werkzeug**: WSGI utilities and secure file handling

### Database
- **SQLAlchemy**: Database abstraction layer supporting multiple backends
- **Connection Pooling**: Configured with pool recycling and pre-ping for reliability

### Infrastructure
- **File Storage**: Local filesystem for document uploads
- **Environment Configuration**: Environment variables for sensitive configuration
- **Logging**: Python logging for debugging and monitoring