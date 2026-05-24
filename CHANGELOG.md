# Changelog

All notable changes to AI Teacher Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2026-05-24

### 🎯 Added

- **Agentic Functions**: Advanced autonomous workflow capabilities for intelligent task routing and execution
- **Intelligent Task Routing**: Adaptive system for distributing complex tasks between bot components
- **Autonomous Workflow Execution**: Multi-step process execution with automatic error recovery and fallback mechanisms
- **Enhanced Learning**: Adaptive error handling based on task execution results
- **Improved Service Integration**: Better coordination between homework generation, payment processing, and lesson management
- **Extended Logging**: Comprehensive logging for workflow debugging and monitoring

### 🔧 Improved

- Optimized background job processing and scheduling
- Enhanced homework validation pipeline with better error recovery
- Improved performance of recurring lesson materialization
- Better rate limiting and resource utilization
- More robust database transaction handling
- Refined middleware chain for faster request processing

### 📚 Documentation

- Translated DEPLOY.md to English
- Translated QA_GUIDE.md to English
- Added comprehensive architecture documentation
- Created usage examples for agentic features
- Updated QA guide excluded from repository

### 🐛 Fixed

- Edge cases in recurring lesson scheduling
- Improved error messages for failed homework generation
- Better handling of payment transaction edge cases

---

## [2.0.0] - 2026-04-15

### 🎯 Added

- Core Telegram bot infrastructure with aiogram
- Role-based workflows for teachers and students
- One-time and recurring lesson scheduling with conflict detection
- Student reschedule workflow with approval system
- AI-generated homework with multi-provider support (NVIDIA NIM, Mistral, Groq)
- Interactive homework engine with exercise types and scoring
- Payment tracking system with prepaid lessons and balance management
- Background job automation for reminders and maintenance
- SQLAlchemy ORM persistence layer
- Comprehensive test suite (105+ tests)

### 📝 Architecture

- Layered bot architecture with routers, middleware, and services
- Async-first runtime using aiogram and async SQLAlchemy
- Provider-agnostic AI generation with JSON repair and validation
- Indexed tables and constraints for data integrity
- Versioned database migrations

---

## [1.0.0] - 2026-03-01

### 🎯 Initial Release

- Basic Telegram bot for lesson scheduling
- Simple student/teacher registration
- Calendar-based lesson planning
- Reminder notifications
- Payment balance tracking
