from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Project, Rating, Request
from .forms import ProjectForm
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery, Count, Sum, F
from django.db.models.functions import Coalesce
from django.db.models import Value
from django.contrib.auth.models import User


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
            all_volunteers = User.objects.filter(profile__role='volunteer').select_related('profile').annotate(
                total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
            ).order_by('-total_hours')
            context['ratings'] = [
                {'name': u, 'rating': u.total_hours} for u in all_volunteers
            ]
            context['groups'] = UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name='').values_list('group_name', flat=True).distinct()
        elif hasattr(user, 'profile'):
            context['profile'] = user.profile
            if user.profile.role == 'volunteer':
                template = 'volunteer_app/user_dashboard.html'
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
                all_users = User.objects.all().select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                )
                context['all_users'] = all_users
                context['volunteer_count'] = UserProfile.objects.filter(role='volunteer').count()
                context['organizer_count'] = UserProfile.objects.filter(role='organiser').count()
                context['projects'] = Project.objects.all().order_by('-date')
                all_volunteers = User.objects.filter(profile__role='volunteer').select_related('profile').annotate(
                    total_hours=Coalesce(Sum('requests__event__hours', filter=Q(requests__status='approved')), 0)
                ).order_by('-total_hours')
                context['ratings'] = [
                    {'name': u, 'rating': u.total_hours} for u in all_volunteers
                ]
                context['groups'] = UserProfile.objects.filter(role='volunteer').exclude(group_name__isnull=True).exclude(group_name='').values_list('group_name', flat=True).distinct().order_by('group_name')

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
        Request.objects.get_or_create(Volunteer=request.user, event=project)
        messages.success(request, f'Ви подали заявку на проєкт "{project.name}"')
    return redirect('dashboard')

@login_required
def manage_request(request, request_id, action):
    req = get_object_or_404(Request, id=request_id)
    if request.user.profile.role in ['organiser', 'admin']:
        if action == 'approve':
            req.status = 'approved'
            messages.success(request, f'Заявку від {req.Volunteer.username} схвалено')
        elif action == 'reject':
            req.status = 'rejected'
            messages.success(request, f'Заявку від {req.Volunteer.username} відхилено')
        req.save()
    return redirect('dashboard')

@login_required
def create_project(request):
    if request.method == 'POST' and request.user.profile.role in ['organiser', 'admin']:
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