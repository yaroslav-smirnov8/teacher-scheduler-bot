# Teacher Scheduler Bot

Telegram bot for automated lesson scheduling with database-level conflict detection and state management.

## Features

- **Automated Scheduling** - Teachers and students can schedule lessons through Telegram interface
- **Conflict Detection** - Database-level constraints prevent double-bookings for both teachers and students
- **Multi-step Conversations** - State-based conversation handlers for intuitive user interaction
- **Calendar Integration** - Calendar-based UI with inline keyboards for date/time selection
- **Notifications** - Automated notifications for scheduled, rescheduled, and canceled lessons
- **Student Management** - Teachers can view and manage their student list
- **Rescheduling Workflow** - Students can request lesson rescheduling with teacher approval
- **Role-based Access** - Separate workflows for teacher and student registration/actions

## Architecture

### Components

**bot.py** - Main application entry point
- Conversation handlers for teacher/student registration
- Menu navigation and command handling
- Calendar and scheduling workflows

**models.py** - SQLAlchemy ORM models
- Teacher - Teacher account with students and lessons
- Student - Student account linked to teacher
- Lesson - Scheduled lesson with date, time, teacher and student

**database.py** - Database configuration
- MySQL/PyMySQL connection management
- Session factory with connection pooling
- Automatic database initialization

**services.py** - Business logic layer
- LessonService - Lesson creation, validation, and conflict detection
- NotificationService - Message delivery to users
- UserService - Teacher and student lookups

## Technical Stack

- **Framework:** python-telegram-bot 13.15
- **Database:** MySQL with SQLAlchemy 2.0+
- **ORM:** SQLAlchemy (async-compatible patterns)
- **Configuration:** python-dotenv for environment variables

## Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+ (or MySQL-compatible database)
- Telegram Bot Token

### Setup

1. Clone the repository:
\\\ash
git clone https://github.com/yaroslav-smirnov8/teacher-scheduler-bot.git
cd teacher-scheduler-bot
\\\

2. Create virtual environment:
\\\ash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
\\\

3. Install dependencies:
\\\ash
pip install -r requirements.txt
\\\

4. Configure environment variables in \.env\:
\\\
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/teacherdb?charset=utf8mb4
\\\

5. Run the bot:
\\\ash
python bot.py
\\\

## Database Schema

### Teachers Table
- id - Primary key
- 
ame - Full name
- contact_info - Contact information
- login - Unique login identifier
- 	elegram_id - Unique Telegram user ID

### Students Table
- id - Primary key
- 
ame - Student name
- contact_info - Contact information
- 	eacher_id - Foreign key to teacher
- 	elegram_id - Unique Telegram user ID

### Lessons Table
- id - Primary key
- date - Lesson date
- 	ime - Lesson time
- 	eacher_id - Foreign key to teacher
- student_id - Foreign key to student
- Unique constraint on (teacher_id, date, time)
- Unique constraint on (student_id, date, time)

## User Workflows

### Teacher Registration
1. /register_teacher command
2. Provide name, contact info, and create login
3. Account created with automatic Telegram ID linking

### Teacher Actions
- View calendar with scheduled lessons
- View student list
- View personal schedule
- Receive notifications for lesson events

### Student Registration
1. /register_student command
2. Provide teacher login
3. Account linked to teacher

### Student Actions
- Request lesson rescheduling
- Provide reason for rescheduling
- Receive notifications
- View assigned lessons

## Conflict Detection

The system prevents scheduling conflicts at two levels:

1. **Database Constraints** - Unique constraints on (teacher_id/student_id, date, time) combinations prevent conflicts at the database level
2. **Service Layer Validation** - \LessonService.check_time_conflict()\ validates before attempting to insert

This ensures data integrity even with concurrent requests.

## Testing

Run tests (if configured):
\\\ash
pip install -r requirements-test.txt
pytest
\\\

## Key Implementation Details

- **Transaction Management** - SQLAlchemy sessions handle ACID properties
- **State Management** - ConversationHandler maintains user state across multi-step workflows
- **Connection Pooling** - Database connection pool configured with 3600-second recycle time
- **Unicode Support** - UTF-8 charset configuration for international character support
- **Error Handling** - Graceful error messages for conflict scenarios

## Limitations and Design Decisions

- Time slots are locked to exact times (no 15-minute intervals) - can be extended
- Calendar navigation is limited to current/future dates
- No lesson modification after scheduling (only rescheduling via student request workflow)
- Single timezone support (system timezone)

## Development

The codebase is organized following a layered architecture:
- **Presentation Layer** - Telegram handlers and conversations
- **Business Logic Layer** - Services (LessonService, UserService, NotificationService)
- **Data Access Layer** - SQLAlchemy models and database configuration
