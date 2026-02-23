from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from volunteer_app.models import User, Task

class Command(BaseCommand):
    help = 'Create sample tasks for testing'

    def handle(self, *args, **options):
        # Знаходимо організатора
        try:
            organizer = User.objects.filter(role='organizer').first()
            if not organizer:
                self.stdout.write(self.style.ERROR('No organizer found. Please create an organizer first.'))
                return
            
            # Створюємо тестові завдання
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
                    'due_date': timezone.now().date() + timedelta(days=3),
                    'estimated_hours': 2.5,
                    'location': 'Притулок "Друг", вул. Садова 15'
                },
                {
                    'title': 'Організація благодійного ярмарку',
                    'description': 'Підготовка та проведення благодійного ярмарку',
                    'due_date': timezone.now().date() + timedelta(days=5),
                    'estimated_hours': 4.0,
                    'location': 'Площа Свободи, центр міста'
                },
                {
                    'title': 'Допомога літнім людям',
                    'description': 'Доставка продуктів та допомога по господарству літнім людям',
                    'due_date': timezone.now().date() + timedelta(days=1),
                    'estimated_hours': 2.0,
                    'location': 'Район житлових будинків'
                },
                {
                    'title': 'Прибирання пляжу',
                    'description': 'Екологічна акція з прибирання міського пляжу',
                    'due_date': timezone.now().date() + timedelta(days=7),
                    'estimated_hours': 3.5,
                    'location': 'Міський пляж, вул. Набережна'
                }
            ]
            
            created_count = 0
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
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created task: {task.title}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} sample tasks'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating tasks: {str(e)}'))
