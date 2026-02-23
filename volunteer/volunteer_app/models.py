from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import models
from django.db import IntegrityError


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('volunteer', 'Волонтер'),
        ('organiser', 'Організатор'),
        ('admin', 'Адміністратор'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='volunteer')
    group_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Група (наприклад, IT-21)")

    def __str__(self):
        return f'{self.user.username} - {self.role}'


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
        except IntegrityError:
            pass





class Project(models.Model):

    ACTION = [
        ('apply', 'Подати заявку'),
        ('approved', 'Схвалено'),
        ('pending', 'Заявку подано'),
        ('rejected', 'Заявку відхилено'),]

    name = models.CharField(max_length=255)
    organiser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organised_projects')
    date = models.DateTimeField()
    hours = models.PositiveIntegerField()
    max_volunteers = models.PositiveIntegerField(default=0, verbose_name="Максимальна кількість волонтерів (0 - без обмежень)")
    status = models.CharField(max_length=20, choices=ACTION, default='apply')

    def __str__(self):
        return self.name


class Rating(models.Model):
    name = models.ForeignKey(User, related_name='ratings', on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()

    def __str__(self):
        return self.name
    

class Request(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В очікуванні'),
        ('approved', 'Схвалено'),
        ('rejected', 'Відхилено'),
    ]
    Volunteer = models.ForeignKey(User, related_name='requests', on_delete=models.CASCADE)
    event = models.ForeignKey(Project, related_name='requests', on_delete=models.DO_NOTHING)
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f'{self.Volunteer.username} -> {self.event.name} ({self.status})'
    