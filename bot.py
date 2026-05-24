import logging
import calendar
import os
from datetime import datetime, date, time, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, relying on system environment

from models import Teacher, Student, Lesson
from database import init_db, SessionLocal as Session
from services import LessonService, NotificationService, UserService

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database initialization
init_db()

# Bot initialization
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# States for teacher and student registration
NAME, CONTACT, LOGIN, TEACHER_LOGIN, STUDENT_NAME, STUDENT_CONTACT = range(6)
SELECT_LESSON, REASON, NEW_TIME = range(10, 13)

def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Calendar", callback_data='calendar')],
        [InlineKeyboardButton("My Students", callback_data='list_students')],
        [InlineKeyboardButton("My Schedule", callback_data='my_schedule')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome! I'm your educational bot.", reply_markup=reply_markup)

def handle_main_menu(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'calendar':
        show_calendar_callback(update, context)
    elif query.data == 'list_students':
        list_students_callback(update, context)
    elif query.data == 'my_schedule':
        my_schedule_callback(update, context)

def register_teacher_start(update, context):
    update.message.reply_text('Please enter your name:')
    return NAME

def register_teacher_name(update, context):
    context.user_data['name'] = update.message.text
    update.message.reply_text('Enter your contact information:')
    return CONTACT

def register_teacher_contact(update, context):
    context.user_data['contact'] = update.message.text
    update.message.reply_text('Create a login:')
    return LOGIN

def register_teacher_login(update, context):
    session = Session()
    try:
        name = context.user_data['name']
        contact = context.user_data['contact']
        login = update.message.text
        chat_id = update.message.from_user.id

        if session.query(Teacher).filter_by(login=login).first():
            update.message.reply_text("This login is already in use. Please choose another one.")
            return LOGIN

        new_teacher = Teacher(name=name, contact_info=contact, login=login, telegram_id=chat_id)
        session.add(new_teacher)
        session.commit()
        update.message.reply_text(f"You have successfully registered as a teacher. Your login: {login}")
        return ConversationHandler.END
    finally:
        session.close()

def register_student_start(update, context):
    update.message.reply_text('Please enter the teacher login:')
    return TEACHER_LOGIN

def register_student_login(update, context):
    session = Session()
    try:
        chat_id = update.message.from_user.id
        username = update.message.from_user.username

        if session.query(Student).filter_by(telegram_id=chat_id).first():
            update.message.reply_text("You are already registered as a student.")
            return ConversationHandler.END

        teacher_login = update.message.text
        teacher = session.query(Teacher).filter_by(login=teacher_login).first()
        if not teacher:
            update.message.reply_text("Teacher with this login not found.")
            return TEACHER_LOGIN

        new_student = Student(name=username, telegram_id=chat_id, teacher=teacher)
        session.add(new_student)
        session.commit()
        update.message.reply_text(f"You have successfully registered as a student. Your teacher: {teacher.name}")
        return ConversationHandler.END
    finally:
        session.close()

def add_student_start(update, context):
    update.message.reply_text('Enter student name:')
    return STUDENT_NAME

def add_student_name(update, context):
    context.user_data['student_name'] = update.message.text
    update.message.reply_text('Enter student contact information:')
    return STUDENT_CONTACT

def add_student_contact(update, context):
    session = Session()
    try:
        chat_id = update.message.from_user.id
        teacher = session.query(Teacher).filter_by(telegram_id=chat_id).first()

        if teacher is None:
            update.message.reply_text("You are not registered as a teacher.")
            return ConversationHandler.END

        student_name = context.user_data['student_name']
        student_contact = update.message.text

        new_student = Student(name=student_name, contact_info=student_contact, teacher=teacher)
        session.add(new_student)
        session.commit()
        update.message.reply_text(f"Student {student_name} successfully added.")
        return ConversationHandler.END
    finally:
        session.close()

def cancel(update, context):
    update.message.reply_text('Process cancelled.')
    return ConversationHandler.END

def list_students(update, context):
    session = Session()
    try:
        chat_id = update.message.from_user.id
        teacher = session.query(Teacher).filter_by(telegram_id=chat_id).first()

        if teacher is None:
            update.message.reply_text("You are not registered as a teacher.")
            return

        students = session.query(Student).filter_by(teacher_id=teacher.id).all()
        if not students:
            update.message.reply_text("You have no students.")
            return

        response = "Your students:\n" + "\n".join(
            [f"{student.name}, Contacts: {student.contact_info or 'Not specified'}" for student in students])
        update.message.reply_text(response)
    finally:
        session.close()

def list_students_callback(update, context):
    query = update.callback_query
    session = Session()
    try:
        chat_id = query.from_user.id
        teacher = session.query(Teacher).filter_by(telegram_id=chat_id).first()

        if teacher is None:
            query.edit_message_text("You are not registered as a teacher.")
            return

        students = session.query(Student).filter_by(teacher_id=teacher.id).all()
        if not students:
            query.edit_message_text("You have no students.")
            return

        response = "Your students:\n" + "\n".join(
            [f"{student.name}, Contacts: {student.contact_info or 'Not specified'}" for student in students])
        query.edit_message_text(response)
    finally:
        session.close()

def create_calendar(year=None, month=None):
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    data_ignore = "IGNORE"
    keyboard = []
    # First row - Month and Year
    row = []
    row.append(InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data=data_ignore))
    keyboard.append(row)
    # Second row - Days of the week
    row = []
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        row.append(InlineKeyboardButton(day, callback_data=data_ignore))
    keyboard.append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"CALENDAR-DAY-{year}-{month}-{day}"))
        keyboard.append(row)

    prev_month, prev_year = (month - 1, year) if month > 1 else (12, year - 1)
    next_month, next_year = (month + 1, year) if month < 12 else (1, year + 1)
    row = [
        InlineKeyboardButton("<", callback_data=f"PREV-MONTH-{prev_year}-{prev_month}"),
        InlineKeyboardButton(" ", callback_data="IGNORE"),
        InlineKeyboardButton(">", callback_data=f"NEXT-MONTH-{next_year}-{next_month}")
    ]
    keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def calendar_handler(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("IGNORE"):
        return
    elif data.startswith("CALENDAR-DAY-"):
        _, date_info = data.split("CALENDAR-DAY-", 1)
        year, month, day = map(int, date_info.split('-'))
        teacher_id = query.from_user.id

        logger.info(f"Checking lessons on {year}-{month}-{day} for teacher {teacher_id}")

        session = Session()
        try:
            teacher = session.query(Teacher).filter_by(telegram_id=teacher_id).first()
            if teacher:
                lessons = session.query(Lesson).filter(
                    Lesson.teacher_id == teacher.id,
                    Lesson.date == date(year, month, day)
                ).all()
                if not lessons:
                    logger.info(f"No lessons scheduled for {year}-{month}-{day}.")
                    keyboard = [
                        [InlineKeyboardButton("Schedule Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")]
                    ]
                    query.edit_message_text(text=f"No lessons scheduled for {day}-{month}-{year}.", reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    logger.info(f"Schedule for {year}-{month}-{day}: {lessons}")
                    schedule_text = "\n".join([f"{i+1}. {lesson.time.strftime('%H:%M')} - {lesson.student.name if lesson.student else 'Unknown'}" for i, lesson in enumerate(lessons)])
                    keyboard = [
                        [InlineKeyboardButton("Add Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")]
                    ]
                    for i, lesson in enumerate(lessons):
                        keyboard.append([InlineKeyboardButton(f"✖️ Cancel Lesson {i+1}", callback_data=f"CANCEL-LESSON-{lesson.id}")])
                    query.edit_message_text(text=f"Schedule for {day}-{month}-{year}:\n{schedule_text}", reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            session.close()
    elif data.startswith("PREV-MONTH") or data.startswith("NEXT-MONTH"):
        _, action, year_month = data.split("-", 2)
        year, month = map(int, year_month.split("-"))
        query.edit_message_text(text="Select date:", reply_markup=create_calendar(year, month))

def show_calendar(update, context):
    now = datetime.now()
    update.message.reply_text("Select date:", reply_markup=create_calendar(now.year, now.month))

def show_calendar_callback(update, context):
    query = update.callback_query
    now = datetime.now()
    query.edit_message_text("Select date:", reply_markup=create_calendar(now.year, now.month))

def confirm_cancel_lesson(update, context):
    from database import get_session
    
    query = update.callback_query
    query.answer()
    
    if not query.data.startswith("CANCEL-LESSON-"):
        return
    
    lesson_id = int(query.data.split("-")[-1])
    
    with get_session() as session:
        success, message, lesson = LessonService.cancel_lesson(session, lesson_id)
        
        if not success:
            query.edit_message_text(message)
            return
        
        # Notify student
        if lesson and lesson.student:
            NotificationService.notify_student_lesson_cancelled(
                context.bot, lesson.student, lesson.teacher,
                lesson.date, lesson.time
            )
        
        query.edit_message_text("Lesson cancelled.")

def schedule_lesson_select_student(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("SCHEDULE-LESSON-"):
        _, date_info = data.split("SCHEDULE-LESSON-", 1)
        year, month, day = map(int, date_info.split('-'))
        context.user_data['schedule_date'] = (year, month, day)

        session = Session()
        try:
            chat_id = query.from_user.id
            teacher = session.query(Teacher).filter_by(telegram_id=chat_id).first()

            if not teacher:
                query.edit_message_text("You are not registered as a teacher.")
                return
            
            students = session.query(Student).filter_by(teacher_id=teacher.id).all()
            if not students:
                query.edit_message_text("You have no students to schedule a lesson with.")
                return
            keyboard = [[InlineKeyboardButton(student.name, callback_data=f"SCHEDULE-TIME-{student.id}")] for student in students]
            query.edit_message_text("Select student:", reply_markup=InlineKeyboardMarkup(keyboard))
        finally:
            session.close()

def schedule_lesson_select_time(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("SCHEDULE-TIME-"):
        student_id = int(data.split("-")[-1])
        context.user_data['student_id'] = student_id

        keyboard = [[InlineKeyboardButton(f"{hour}:00", callback_data=f"CONFIRM-LESSON-{hour}")] for hour in range(6, 24)]
        query.edit_message_text("Select time:", reply_markup=InlineKeyboardMarkup(keyboard))

def confirm_lesson(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("CONFIRM-LESSON-"):
        hour = int(data.split("-")[-1])
        student_id = context.user_data['student_id']
        year, month, day = context.user_data['schedule_date']

        session = Session()
        try:
            teacher = session.query(Teacher).filter_by(telegram_id=query.from_user.id).first()
            if not teacher:
                query.edit_message_text("You are not registered as a teacher.")
                return

            lesson_date = date(year, month, day)
            lesson_time = time(hour, 0)
            
            # Check for past date
            if lesson_date < datetime.now().date():
                query.edit_message_text("Cannot schedule a lesson for a past date.")
                return

            # Check teacher and student availability
            existing_lesson_teacher = session.query(Lesson).filter(
                Lesson.teacher_id == teacher.id,
                Lesson.date == lesson_date,
                Lesson.time == lesson_time
            ).first()

            existing_lesson_student = session.query(Lesson).filter(
                Lesson.student_id == student_id,
                Lesson.date == lesson_date,
                Lesson.time == lesson_time
            ).first()

            if existing_lesson_teacher:
                query.edit_message_text(f"On {day}-{month}-{year} at {hour}:00 the teacher already has a lesson scheduled.")
                return

            if existing_lesson_student:
                query.edit_message_text(f"On {day}-{month}-{year} at {hour}:00 the student already has a lesson scheduled.")
                return

            success, message, lesson = LessonService.create_lesson(
                session, teacher.id, student_id, lesson_date, lesson_time
            )
            
            if not success:
                query.edit_message_text(message)
                return
            
            logger.info(f"Lesson scheduled for {day}-{month}-{year} at {hour}:00.")
            
            # Notify student
            student = session.query(Student).filter_by(id=student_id).first()
            if student:
                NotificationService.notify_student_lesson_created(
                    context.bot, student, teacher, lesson_date, lesson_time
                )

            query.edit_message_text(f"Lesson scheduled for {day}-{month}-{year} at {hour}:00.")
        finally:
            session.close()


def my_schedule(update, context):
    session = Session()
    try:
        chat_id = update.message.from_user.id
        student = session.query(Student).filter_by(telegram_id=chat_id).first()

        if student is None:
            update.message.reply_text("You are not registered as a student.")
            return

        today = datetime.now().date()
        lessons = session.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time).all()
        
        if not lessons:
            update.message.reply_text("You have no scheduled lessons.")
        else:
            schedule_text = "Your schedule:\n" + "\n".join(
                [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.teacher.name}" for lesson in lessons])
            update.message.reply_text(schedule_text)
    finally:
        session.close()

def my_schedule_callback(update, context):
    query = update.callback_query
    session = Session()
    try:
        chat_id = query.from_user.id
        student = session.query(Student).filter_by(telegram_id=chat_id).first()

        if student is None:
            query.edit_message_text("You are not registered as a student.")
            return

        today = datetime.now().date()
        lessons = session.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time).all()
        
        if not lessons:
            query.edit_message_text("You have no scheduled lessons.")
        else:
            schedule_text = "Your schedule:\n" + "\n".join(
                [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.teacher.name}" for lesson in lessons])
            query.edit_message_text(schedule_text)
    finally:
        session.close()


def request_reschedule(update, context):
    session = Session()
    try:
        chat_id = update.message.from_user.id
        student = session.query(Student).filter_by(telegram_id=chat_id).first()

        if student is None:
            update.message.reply_text("You are not registered as a student.")
            return ConversationHandler.END

        today = datetime.now().date()
        lessons = session.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time).all()
        
        if not lessons:
            update.message.reply_text("You have no scheduled lessons.")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton(f"{lesson.date} {lesson.time.strftime('%H:%M')}",
                                          callback_data=f"SELECT-LESSON-{lesson.id}")] for lesson in lessons]
        update.message.reply_text("Select lesson to reschedule:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_LESSON
    finally:
        session.close()


def select_lesson(update, context):
    query = update.callback_query
    query.answer()

    lesson_id = int(query.data.split("-")[-1])
    context.user_data['lesson_id'] = lesson_id

    query.edit_message_text("Enter reason for rescheduling the lesson:")
    return REASON


def reschedule_reason(update, context):
    reason = update.message.text
    context.user_data['reason'] = reason
    keyboard = [[InlineKeyboardButton(f"{hour}:00", callback_data=f"NEW-TIME-{hour}")] for hour in range(6, 24)]
    update.message.reply_text("Select new time:", reply_markup=InlineKeyboardMarkup(keyboard))
    return NEW_TIME


def confirm_reschedule(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("NEW-TIME-"):
        hour = int(data.split("-")[-1])
        context.user_data['new_hour'] = hour
        lesson_id = context.user_data['lesson_id']
        reason = context.user_data['reason']

        session = Session()
        try:
            lesson = session.query(Lesson).filter_by(id=lesson_id).first()
            if not lesson:
                query.edit_message_text("Lesson not found.")
                return ConversationHandler.END
            
            # Check for past date
            if lesson.date < datetime.now().date():
                query.edit_message_text("Cannot reschedule a lesson in the past.")
                return ConversationHandler.END
            
            teacher = lesson.teacher
            new_time = time(hour, 0)
            lesson_time = datetime.combine(lesson.date, new_time)
            teacher_id = lesson.teacher_id
            student_id = lesson.student_id

            # Check teacher and student availability
            existing_lesson_teacher = session.query(Lesson).filter(
                Lesson.teacher_id == teacher_id,
                Lesson.date == lesson.date,
                Lesson.time == new_time
            ).first()

            existing_lesson_student = session.query(Lesson).filter(
                Lesson.student_id == student_id,
                Lesson.date == lesson.date,
                Lesson.time == new_time
            ).first()

            if existing_lesson_teacher:
                query.edit_message_text(f"On {lesson.date} at {hour}:00 the teacher already has a lesson scheduled.")
                return ConversationHandler.END
            
            if existing_lesson_student:
                query.edit_message_text(f"On {lesson.date} at {hour}:00 the student already has a lesson scheduled.")
                return ConversationHandler.END

            # Send message to teacher
            teacher_chat_id = teacher.telegram_id
            if teacher_chat_id:
                context.bot.send_message(chat_id=teacher_chat_id,
                                         text=f"Student {lesson.student.name} requests to reschedule lesson from {lesson.time.strftime('%H:%M')} to {hour}:00 for reason: {reason}. Do you agree?",
                                         reply_markup=InlineKeyboardMarkup([
                                             [InlineKeyboardButton("Reschedule",
                                                                   callback_data=f"ACCEPT-RESCHEDULE-{lesson.id}-{hour}")],
                                             [InlineKeyboardButton("Decline",
                                                                   callback_data=f"DECLINE-RESCHEDULE-{lesson.id}")]
                                         ]))
            query.edit_message_text("Request to reschedule lesson sent to teacher.")
        finally:
            session.close()
    return ConversationHandler.END


def accept_reschedule(update, context):
    from services import LessonService, NotificationService
    from database import get_session
    
    query = update.callback_query
    query.answer()

    if not query.data.startswith("ACCEPT-RESCHEDULE-"):
        return
    
    parts = query.data.split("-")
    lesson_id = int(parts[2])
    hour = int(parts[3])
    new_time = time(hour, 0)

    with get_session() as session:
        success, message = LessonService.reschedule_lesson(session, lesson_id, new_time)
        
        if not success:
            query.edit_message_text(message)
            return
        
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if lesson and lesson.student:
            NotificationService.notify_student_reschedule_result(
                context.bot, lesson.student, lesson.teacher, 
                lesson.date, new_time, accepted=True
            )
        
        query.edit_message_text("Lesson rescheduled.")


def decline_reschedule(update, context):
    from services import NotificationService
    from database import get_session
    
    query = update.callback_query
    query.answer()

    if not query.data.startswith("DECLINE-RESCHEDULE-"):
        return
    
    lesson_id = int(query.data.split("-")[-1])

    with get_session() as session:
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            query.edit_message_text("Lesson not found.")
            return
        
        if lesson.student:
            NotificationService.notify_student_reschedule_result(
                context.bot, lesson.student, lesson.teacher,
                lesson.date, lesson.time, accepted=False
            )
        
        query.edit_message_text("Request to reschedule lesson declined.")


teacher_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('register_teacher', register_teacher_start)],
    states={
        NAME: [MessageHandler(Filters.text & ~Filters.command, register_teacher_name)],
        CONTACT: [MessageHandler(Filters.text & ~Filters.command, register_teacher_contact)],
        LOGIN: [MessageHandler(Filters.text & ~Filters.command, register_teacher_login)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

student_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('register_student', register_student_start)],
    states={
        TEACHER_LOGIN: [MessageHandler(Filters.text & ~Filters.command, register_student_login)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

add_student_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('add_student', add_student_start)],
    states={
        STUDENT_NAME: [MessageHandler(Filters.text & ~Filters.command, add_student_name)],
        STUDENT_CONTACT: [MessageHandler(Filters.text & ~Filters.command, add_student_contact)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

reschedule_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('reschedule', request_reschedule)],
    states={
        SELECT_LESSON: [CallbackQueryHandler(select_lesson, pattern='^SELECT-LESSON-')],
        REASON: [MessageHandler(Filters.text & ~Filters.command, reschedule_reason)],
        NEW_TIME: [CallbackQueryHandler(confirm_reschedule, pattern='^NEW-TIME-')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)



dispatcher.add_handler(teacher_conv_handler)
dispatcher.add_handler(student_conv_handler)
dispatcher.add_handler(add_student_conv_handler)
dispatcher.add_handler(reschedule_conv_handler)
dispatcher.add_handler(CallbackQueryHandler(handle_main_menu, pattern='^(calendar|list_students|my_schedule)$'))
dispatcher.add_handler(CallbackQueryHandler(calendar_handler, pattern='CALENDAR-DAY-'))
dispatcher.add_handler(CallbackQueryHandler(schedule_lesson_select_student, pattern='SCHEDULE-LESSON-'))
dispatcher.add_handler(CallbackQueryHandler(schedule_lesson_select_time, pattern='SCHEDULE-TIME-'))
dispatcher.add_handler(CallbackQueryHandler(confirm_lesson, pattern='CONFIRM-LESSON-'))
dispatcher.add_handler(CallbackQueryHandler(calendar_handler, pattern='^(PREV-MONTH|NEXT-MONTH)'))
dispatcher.add_handler(CallbackQueryHandler(accept_reschedule, pattern='ACCEPT-RESCHEDULE-'))
dispatcher.add_handler(CallbackQueryHandler(decline_reschedule, pattern='DECLINE-RESCHEDULE-'))
dispatcher.add_handler(CallbackQueryHandler(confirm_cancel_lesson, pattern='CANCEL-LESSON-'))
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('list_students', list_students))
dispatcher.add_handler(CommandHandler('calendar', show_calendar))
dispatcher.add_handler(CommandHandler('my_schedule', my_schedule))

try:
    logger.info("Starting bot...")
    updater.start_polling()
    logger.info("Bot started successfully")
    updater.idle()
except Exception as e:
    logger.error(f"Error starting bot: {e}")
    raise