from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Project, Rating, Request
from .forms import ProjectForm
from django.db.models import Q, Sum, OuterRef, Subquery, Count, Sum as SumModel, F
from django.db.models.functions import Coalesce
from django.db.models import Value


def extract_course(group_name):
    """Extract course number from group name (e.g., IT-21 -> 2, IT-11 -> 1)"""
    if not group_name:
        return None
    for char in group_name:
        if char.isdigit():
            return int(char)
    return None


def get_volunteer_hours(user):
    """Calculate total volunteer hours for a user"""
    from .models import Request
    result = Request.objects.filter(
        Volunteer=user,
        status='approved'
    ).aggregate(total=Sum('event__hours'))
    return result['total'] or 0


def landing(request):
    return render(request, 'volunteer_app/landing.html')

@csrf_exempt
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    error_message = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
            
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    error_message = "Невірний пароль"
            else:
                error_message = "Користувача з таким email не знайдено"
        except User.MultipleObjectsReturned:
            error_message = "Виявлено декілька користувачів з цим email. Зверніться до адміністратора."

    return render(request, 'volunteer_app/login.html', {'error': error_message})


@login_required
def dashboard(request):
    user = request.user
    context = {}

    if request.method == 'POST' and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')):
        role = request.POST.get('role')
        full_name = request.POST.get('full_name')
        group_name = request.POST.get('group_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            username = email.split('@')[0]
            # Generate unique username if exists
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            new_user = User.objects.create_user(username=username, email=email, password=password)
            if full_name:
                names = full_name.split(' ')
                new_user.first_name = names[0]
                if len(names) > 1:
                    new_user.last_name = ' '.join(names[1:])
            new_user.save()
            
            # Check if profile already exists
            profile, created = UserProfile.objects.get_or_create(user=new_user)
            # Admin dashboard roles are 'volunteer', 'organizer', 'admin'
            if role == 'organizer': role = 'organiser' 
            profile.role = role if role in ['volunteer', 'organiser', 'admin'] else 'volunteer'
            if group_name:
                profile.group_name = group_name
            profile.save()
            messages.success(request, f'Користувача {email} успішно створено')
            return redirect('dashboard')
    
    try:
        if user.is_superuser:
            template = 'volunteer_app/admin_dashboard.html'
            all_users = User.objects.all().select_related('profile').annotate(
                total_hours=Sum('requests__event__hours', filter=Q(requests__status='approved'))
            )
            context['all_users'] = all_users
            context['volunteer_count'] = UserProfile.objects.filter(role='volunteer').count()
            context['organizer_count'] = UserProfile.objects.filter(role='organiser').count()
            context['projects'] = Project.objects.all().order_by('-date')
            context['all_requests'] = Request.objects.all().order_by('-date_requested')
            all_volunteers = User.objects.filter(profile__role='volunteer').select_related('profile').annotate(
                total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
            ).order_by('-total_hours')
            context['ratings'] = [
                {'name': u, 'rating': u.total_hours} for u in all_volunteers
            ]
            context['groups'] = UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name='').values_list('group_name', flat=True).distinct().order_by('group_name')
            imported_students = request.session.pop('imported_students', None)
            if imported_students:
                context['imported_students'] = imported_students
        elif hasattr(user, 'profile'):
            context['profile'] = user.profile
            if user.profile.role == 'volunteer':
                template = 'volunteer_app/user_dashboard.html'
                context['projects'] = Project.objects.all().order_by('-date')
                user_requests = Request.objects.filter(Volunteer=user)
                context['activities'] = user_requests.order_by('-date_requested')
                context['joined_opportunities'] = user_requests.filter(status='approved')
                
                user_req_subquery = Request.objects.filter(
                    Volunteer=user, 
                    event=OuterRef('pk')
                ).values('status')[:1]
                
                context['opportunities'] = Project.objects.annotate(
                    application_status=Subquery(user_req_subquery)
                ).order_by('-date')
                
                all_volunteers = User.objects.filter(profile__role='volunteer').select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                ).order_by('-total_hours')
                context['ratings'] = [
                    {'name': u, 'rating': u.total_hours} for u in all_volunteers
                ]

            elif user.profile.role == 'organiser':
                template = 'volunteer_app/organizer_dashboard.html'
                context['projects'] = Project.objects.filter(organiser=user).order_by('-date')
                context['applicants'] = Request.objects.filter(event__organiser=user).order_by('-date_requested')
                context['project_form'] = ProjectForm()
                context['all_users'] = User.objects.all().select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                )
                context['groups'] = UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name='').values_list('group_name', flat=True).distinct().order_by('group_name')

            elif user.profile.role == 'admin':
                template = 'volunteer_app/admin_dashboard.html'
                all_users = list(User.objects.all().select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                ))
                for u in all_users:
                    group_name = u.profile.group_name if u.profile else None
                    u.course = extract_course(group_name) if group_name else None
                all_users = sorted(all_users, key=lambda x: (x.course is None, x.course or 0))
                context['all_users'] = all_users
                context['volunteer_count'] = UserProfile.objects.filter(role='volunteer').count()
                context['organizer_count'] = UserProfile.objects.filter(role='organiser').count()
                context['projects'] = Project.objects.all().order_by('-date')
                context['all_requests'] = Request.objects.all().order_by('-date_requested')
                all_volunteers = User.objects.filter(profile__role='volunteer').select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                ).order_by('-total_hours')
                context['ratings'] = [
                    {'name': u, 'rating': u.total_hours} for u in all_volunteers
                ]
                
                courses = []
                for profile in UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name=''):
                    course = extract_course(profile.group_name)
                    if course and course not in courses:
                        courses.append(course)
                courses.sort()
                available_courses = [1, 2]
                courses = sorted(set(courses + available_courses))
                context['courses'] = courses
                context['groups'] = UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name='').values_list('group_name', flat=True).distinct().order_by('group_name')
                imported_students = request.session.pop('imported_students', None)
                if imported_students:
                    context['imported_students'] = imported_students

            else:
                template = 'volunteer_app/landing.html'
        else:
            template = 'volunteer_app/landing.html'
    except Exception as e:
        print(f"Error in dashboard: {e}")
        template = 'volunteer_app/landing.html'

    return render(request, template, context)

@login_required
def apply_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user.profile.role == 'volunteer':
        existing_request = Request.objects.filter(Volunteer=request.user, event=project).first()
        if not existing_request:
            Request.objects.create(Volunteer=request.user, event=project, status='pending')
            if project.max_volunteers > 0:
                project.current_volunteers += 1
                project.save()
            messages.success(request, f'Ви подали заявку на проєкт "{project.name}"')
        else:
            messages.info(request, 'Ви вже подали заявку на цей проєкт')
    return redirect('dashboard')

@login_required
def manage_request(request, request_id, action):
    req = get_object_or_404(Request, id=request_id)
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role in ['organiser', 'admin']):
        if action == 'approve':
            req.status = 'approved'
            hours = request.POST.get('hours')
            if hours:
                try:
                    req.approved_hours = int(hours)
                except (ValueError, TypeError):
                    req.approved_hours = req.event.hours
            else:
                req.approved_hours = req.event.hours
            messages.success(request, f'Заявку від {req.Volunteer.username} схвалено')
        elif action == 'reject':
            req.status = 'rejected'
            messages.success(request, f'Заявку від {req.Volunteer.username} відхилено')
        elif action == 'complete':
            req.status = 'completed'
            hours = request.POST.get('hours')
            if hours:
                try:
                    req.approved_hours = int(hours)
                except (ValueError, TypeError):
                    req.approved_hours = req.event.hours
            else:
                req.approved_hours = req.event.hours
            messages.success(request, f'Волонтеру {req.Volunteer.username} зараховано {req.approved_hours} годин')
        req.save()
        project = req.event
        if action == 'approve' and project.max_volunteers > 0:
            project.current_volunteers += 1
            project.save()
    return redirect('dashboard')

@login_required
def report_volunteer(request, request_id):
    if request.method == 'POST':
        report_text = request.POST.get('report', '').strip()
        req = get_object_or_404(Request, id=request_id)
        if request.user == req.event.organiser or request.user.is_superuser:
            if report_text:
                req.organizer_report = report_text
                req.organizer_reported = True
                req.save()
                messages.success(request, 'Скаргу на волонтера відправлено адміну')
            else:
                messages.error(request, 'Введіть текст скарги')
        else:
            messages.error(request, 'У вас немає доступу')
    return redirect('dashboard')

@login_required
def toggle_star(request, request_id):
    req = get_object_or_404(Request, id=request_id)
    if request.user == req.event.organiser or request.user.is_superuser:
        req.star_rating = not req.star_rating
        req.save()
        if req.star_rating:
            messages.success(request, f'Волонтеру {req.Volunteer.username} додано зірочку за гарну роботу!')
        else:
            messages.success(request, f'Волонтеру {req.Volunteer.username} забрано зірочку')
    return redirect('dashboard')

@login_required
def create_project(request):
    if request.method == 'POST' and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role in ['organiser', 'admin'])):
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.organiser = request.user
            project.save()
            messages.success(request, 'Проєкт успішно створено')
    return redirect('dashboard')

@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user == project.organiser or request.user.is_superuser:
        project.delete()
        messages.success(request, 'Проєкт видалено')
    return redirect('dashboard')

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("landing")
    elif request.method == "GET":
        logout(request)
        return redirect("landing")

@login_required
def profile_view(request):
    user = request.user
    context = {
        'user': user,
    }
    if hasattr(user, 'profile'):
        context['profile'] = user.profile
        
    # Get user's volunteer stats
    if hasattr(user, 'profile') and user.profile.role == 'volunteer':
        from django.db.models import Count, Sum
        from .models import Request
        context['total_events'] = Request.objects.filter(Volunteer=user, status='approved').count()
        context['total_hours'] = Request.objects.filter(Volunteer=user, status='approved').aggregate(total=Sum('event__hours'))['total'] or 0
    
    return render(request, 'volunteer_app/profile.html', context)

@login_required
def view_user_profile(request, username):
    viewed_user = get_object_or_404(User, username=username)
    
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role in ['organiser', 'admin'])):
        messages.error(request, 'У вас немає доступу до цієї сторінки')
        return redirect('dashboard')
    
    context = {
        'viewed_user': viewed_user,
        'profile': viewed_user.profile if hasattr(viewed_user, 'profile') else None,
    }
    
    if hasattr(viewed_user, 'profile') and viewed_user.profile.role == 'volunteer':
        from django.db.models import Count, Sum
        from .models import Request
        context['total_events'] = Request.objects.filter(Volunteer=viewed_user, status='completed').count()
        context['total_hours'] = Request.objects.filter(Volunteer=viewed_user, status='completed').aggregate(total=Sum('approved_hours'))['total'] or 0
        context['user_requests'] = Request.objects.filter(Volunteer=viewed_user).order_by('-date_requested')[:10]
        context['star_count'] = Request.objects.filter(Volunteer=viewed_user, star_rating=True).count()
    
    return render(request, 'volunteer_app/view_profile.html', context)

@login_required
def settings_view(request):
    user = request.user
    context = {
        'user': user,
    }
    if hasattr(user, 'profile'):
        context['profile'] = user.profile
    return render(request, 'volunteer_app/settings.html', context)

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Update profile if exists
        if hasattr(user, 'profile'):
            profile = user.profile
            group_name = request.POST.get('group_name', '').strip()
            if group_name:
                profile.group_name = group_name
            profile.save()
        
        messages.success(request, 'Профіль оновлено')
    return redirect('settings')

@login_required
def update_password(request):
    if request.method == 'POST':
        from django.contrib.auth import update_session_auth_hash
        user = request.user
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if new_password and new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль змінено')
        elif new_password != confirm_password:
            messages.error(request, 'Паролі не співпадають')
        else:
            messages.error(request, 'Введіть новий пароль')
    return redirect('settings')

@login_required
def import_students(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')):
        messages.error(request, 'У вас немає доступу до цієї сторінки')
        return redirect('dashboard')
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Будь ласка, виберіть файл')
            return redirect('dashboard')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Файл повинен бути у форматі CSV')
            return redirect('dashboard')
        
        try:
            decoded_content = csv_file.read().decode('utf-8')
            lines = decoded_content.strip().split('\n')
            
            if len(lines) < 2:
                messages.error(request, 'CSV файл порожній або не містить даних')
                return redirect('dashboard')
            
            imported_count = 0
            errors = []
            imported_students = []
            
            for i, line in enumerate(lines[1:], start=2):
                parts = line.strip().split(',')
                if len(parts) < 3:
                    errors.append(f'Рядок {i}: недостатньо даних')
                    continue
                
                full_name = parts[0].strip()
                group_name = parts[1].strip()
                email = parts[2].strip()
                password = parts[3].strip() if len(parts) > 3 else ''
                
                if not email:
                    errors.append(f'Рядок {i}: відсутній email')
                    continue
                
                if not full_name:
                    full_name = email.split('@')[0]
                
                username = email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                if not password:
                    import random
                    import string
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': full_name.split()[0] if full_name else '',
                        'last_name': ' '.join(full_name.split()[1:]) if full_name else ''
                    }
                )
                
                if created:
                    user.set_password(password)
                    user.save()
                elif password:
                    user.set_password(password)
                    user.save()
                
                profile, profile_created = UserProfile.objects.get_or_create(user=user)
                profile.role = 'volunteer'
                if group_name:
                    profile.group_name = group_name
                profile.save()
                
                imported_count += 1
                imported_students.append({'email': email, 'password': password})
            
            if imported_count > 0:
                request.session['imported_students'] = imported_students
                messages.success(request, f'Успішно імпортовано {imported_count} студентів')
            if errors:
                for error in errors[:5]:
                    messages.warning(request, error)
                    
        except Exception as e:
            messages.error(request, f'Помилка при обробці файлу: {str(e)}')
    
    return redirect('dashboard')

@login_required
def edit_user(request, username):
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')):
        messages.error(request, 'У вас немає доступу')
        return redirect('dashboard')
    
    if request.method == 'POST':
        user = get_object_or_404(User, username=username)
        
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        group_name = request.POST.get('group_name', '').strip()
        role = request.POST.get('role', 'volunteer')
        new_password = request.POST.get('new_password', '').strip()
        
        if email:
            user.email = email
        
        if full_name:
            names = full_name.split(' ', 1)
            user.first_name = names[0]
            user.last_name = names[1] if len(names) > 1 else ''
        
        user.save()
        
        if hasattr(user, 'profile'):
            profile = user.profile
            if role == 'organizer':
                role = 'organiser'
            profile.role = role if role in ['volunteer', 'organiser', 'admin'] else 'volunteer'
            profile.group_name = group_name
            profile.save()
        
        if new_password:
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Пароль для {user.username} змінено')
        
        messages.success(request, f'Користувача {user.username} оновлено')
    
    return redirect('dashboard')

@login_required
def delete_user(request, username):
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')):
        messages.error(request, 'У вас немає доступу')
        return redirect('dashboard')
    
    try:
        user = get_object_or_404(User, username=username)
        if user.is_superuser:
            messages.error(request, 'Неможливо видалити суперкористувача')
            return redirect('dashboard')
        
        user.delete()
        messages.success(request, f'Користувача {username} видалено')
    except Exception as e:
        messages.error(request, f'Помилка при видаленні: {str(e)}')
    
    return redirect('dashboard')

@login_required
def bulk_delete_users(request):
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')):
        messages.error(request, 'У вас немає доступу')
        return redirect('dashboard')
    
    usernames = request.GET.get('usernames', '')
    if not usernames:
        messages.error(request, 'Не вказано користувачів для видалення')
        return redirect('dashboard')
    
    username_list = [u.strip() for u in usernames.split(',') if u.strip()]
    deleted_count = 0
    
    for username in username_list:
        try:
            user = User.objects.get(username=username)
            if not user.is_superuser:
                user.delete()
                deleted_count += 1
        except User.DoesNotExist:
            pass
    
    messages.success(request, f'Видалено {deleted_count} користувачів')
    return redirect('dashboard')