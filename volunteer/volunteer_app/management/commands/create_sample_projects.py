from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from volunteer_app.models import User, Projects

class Command(BaseCommand):
    help = 'Create sample projects for testing'

    def handle(self, *args, **options):
        # Знаходимо організатора
        try:
            organizer = User.objects.filter(role='organizer').first()
            if not organizer:
                self.stdout.write(self.style.ERROR('No organizer found. Please create an organizer first.'))
                return
            
            # Створюємо тестові проекти
            projects_data = [
                {
                    'name': 'Допомога в притулку для тварин',
                    'description': 'Допомога в догляді за тваринами, годування, прибирання вольонтерів',
                    'date': timezone.now().date() + timedelta(days=3),
                    'time': '10:00',
                    'duration_hours': 3.0,
                    'location': 'Притулок "Друг", вул. Садова 15'
                },
                {
                    'name': 'Екологічна акція "Чисте місто"',
                    'description': 'Прибирання сміття, сортування відходів, висадка дерев',
                    'date': timezone.now().date() + timedelta(days=5),
                    'time': '14:00',
                    'duration_hours': 4.0,
                    'location': 'Центральна площа, парк Перемоги'
                },
                {
                    'name': 'Допомога літнім людям',
                    'description': 'Доставка продуктів, допомога по господарству, медичний супровід',
                    'date': timezone.now().date() + timedelta(days=1),
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
                },
                {
                    'name': 'Ремонт дитячого майданчика',
                    'description': 'Фарбування парканів, ремонт ігрового обладнання',
                    'date': timezone.now().date() + timedelta(days=4),
                    'time': '11:00',
                    'duration_hours': 3.5,
                    'location': 'Дитячий майданчик, вул. Шкільна 5'
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
                self.stdout.write(self.style.SUCCESS(f'Created project: {project.name}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} sample projects'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating projects: {str(e)}'))
