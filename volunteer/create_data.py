#!/usr/bin/env python
import os
import sys
import django

sys.path.append('/home/ruslan-pertsovych/Desktop/Diploma/volunteer')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'volunteer.settings')
django.setup()

from volunteer_app.models import User, Projects, Task, Activity
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password

print("Створення тестових даних...")

organizer = User.objects.filter(role='organizer').first()
if not organizer:
    organizer = User.objects.create(
        username='organizer',
        email='organizer@example.com',
        password=make_password('Volunteer2026!'),
        first_name='Організатор',
        role='organizer'
    )
    print("✓ Створено організатора")
else:
    print(f"✓ Організатор існує: {organizer.email}")

projects_data = [
    {
        'name': 'Допомога в притулку для тварин',
        'description': 'Допомога в догляді за тваринами, годування, прибирання вольонтерів',
        'date': timezone.now().date() + timedelta(days=1),
        'time': '10:00',
        'duration_hours': 3.0,
        'location': 'Притулок "Друг", вул. Садова 15'
    },
    {
        'name': 'Екологічна акція "Чисте місто"',
        'description': 'Прибирання сміття, сортування відходів, висадка дерев',
        'date': timezone.now().date() + timedelta(days=3),
        'time': '14:00',
        'duration_hours': 4.0,
        'location': 'Центральна площа, парк Перемоги'
    },
    {
        'name': 'Допомога літнім людям',
        'description': 'Доставка продуктів, допомога по господарству, медичний супровід',
        'date': timezone.now().date() + timedelta(days=5),
        'time': '09:00',
        'duration_hours': 2.5,
        'location': 'Район житлових будинків'
    },
    {
        'name': 'Організація дитячого свята',
        'description': 'Підготовка та проведення свята для дітей з малозабезпечних сімей',
        'date': timezone.now().date() + timedelta(days=7),
        'time': '15:00',
        'duration_hours': 5.0,
        'location': 'Міський будинок культури'
    }
]

created_count = 0
for project_data in projects_data:
    project = Projects.objects.create(
        name=project_data['name'],
        description=project_data['description'],
        organizer=organizer,
        date=project_data['date'],
        time=project_data['time'],
        duration_hours=project_data['duration_hours'],
        location=project_data['location'],
        action='Подано'
    )
    created_count += 1
    print(f"✓ Створено проект: {project.name}")

print(f"✓ Створено {created_count} проектів")

tasks_data = [
    {
        'title': 'Прибрати центральний парк',
        'description': 'Допомога в прибиранні центрального парку міста',
        'due_date': timezone.now().date() + timedelta(days=2),
        'estimated_hours': 3.0,
        'location': 'Центральний парк, вул. Шевченка 1'
    },
    {
        'title': 'Допомога в притулку для тварин',
        'description': 'Годування та догляд за тваринами в міському притулку',
        'due_date': timezone.now().date() + timedelta(days=4),
        'estimated_hours': 2.5,
        'location': 'Притулок "Друг", вул. Садова 15'
    },
    {
        'title': 'Організація благодійного ярмарку',
        'description': 'Підготовка та проведення благодійного ярмарку',
        'due_date': timezone.now().date() + timedelta(days=6),
        'estimated_hours': 4.0,
        'location': 'Площа Свободи, центр міста'
    }
]

created_tasks = 0
for task_data in tasks_data:
    task = Task.objects.create(
        title=task_data['title'],
        description=task_data['description'],
        organizer=organizer,
        due_date=task_data['due_date'],
        estimated_hours=task_data['estimated_hours'],
        location=task_data['location'],
        status='pending'
    )
    created_tasks += 1
    print(f"✓ Створено завдання: {task.title}")

print(f"✓ Створено {created_tasks} завдань")

volunteer = User.objects.filter(role='volunteer').first()
if volunteer:
    activity = Activity.objects.create(
        volunteer=volunteer,
        action='joined',
        description='Приєднався до системи'
    )
    print(f"✓ Створено активність для волонтера: {volunteer.email}")
else:
    print("⚠ Волонтер не знайдений")

print("\n✅ Тестові дані створено успішно!")
