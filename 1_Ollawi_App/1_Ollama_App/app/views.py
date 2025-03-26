"""
Definition of views.
"""

from datetime import datetime
from django.shortcuts import redirect, render
from django.http import HttpRequest
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
import ollama  # For current timestamp
from ollama_backend.models import Presets, Setting
import uuid  # For ID generation

# Setelah login, tampilan halaman pada rute '/' berbeda ketika sebelum login
def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    
    # Check if user is authenticated and prepare different context
    if request.user.is_authenticated:
        context = {
            'title': 'Dashboard',
            'year': datetime.now().year,
            'is_authenticated': True,
            'username': request.user.username,
        }
    else:
        context = {
            'title': 'Welcome',
            'year': datetime.now().year,
            'is_authenticated': False,
        }
    
    return render(request, 'app/index.html', context)

def detailChat(request, id_chat):
    """Renders the detail chat page."""
    assert isinstance(request, HttpRequest)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        # Redirect to login if not authenticated
        return redirect('login')
    
    # Verify that the chat exists and belongs to the current user
    try:
        from ollama_backend.models import Chats
        chat = Chats.objects.get(id=id_chat, id_user=request.user)
    except:
        # If chat doesn't exist or doesn't belong to user, show not found page
        return not_found(request, error_type='chat_not_found')
    
    # Get user's preset for the dropdown
    try:
        user_presets = Presets.objects.filter(id_user=request.user)
        default_preset = user_presets.first()
    except:
        user_presets = []
        default_preset = None
    
    context = {
        'title': 'Chat',
        'year': datetime.now().year,
        'chat_id': id_chat,
        'user_presets': user_presets,
        'default_preset': default_preset,
    }
    
    return render(request, 'app/detailChat.html', context)

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        }
    )

def register(request):
    """Renders the register page and handles user registration."""
    assert isinstance(request, HttpRequest)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password1')
        
        form_errors = {}
        
        # Basic validation
        if not username:
            form_errors['username'] = ['Username is required.']
        if not email:
            form_errors['email'] = ['Email is required.']
        if not password:
            form_errors['password1'] = ['Password is required.']
            
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            form_errors['username'] = ['This username is already taken.']
            
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            form_errors['email'] = ['This email is already registered.']
        
        if not form_errors:
            try:
                # Create user with specified attributes
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=username,  # Set first_name to username
                    is_superuser=False,
                    is_staff=False,
                    is_active=True
                )
                
                # Get the installed models using ollama.list()
                models_data = ollama.list()
                # Extract the list of Model objects
                model_objects = models_data.get('models', [])
                
                # Convert Model objects to dictionaries for JSON serialization
                installed_models = []
                for model in model_objects:
                    model_info = {
                        'name': model.model,
                        'modified_at': model.modified_at.isoformat() if hasattr(model, 'modified_at') else None,
                        'digest': model.digest,
                        'size': model.size,
                    }
                    # Add details if available
                    if hasattr(model, 'details') and model.details:
                        details = model.details
                        model_info['details'] = {
                            'parent_model': details.parent_model,
                            'format': details.format,
                            'family': details.family,
                            'families': details.families,
                            'parameter_size': details.parameter_size,
                            'quantization_level': details.quantization_level
                        }
                    installed_models.append(model_info)
                
                # Create a new setting record for this user
                setting_id = f"setting-{str(uuid.uuid4()).replace('-', '')[:8]}"  # Generate a proper UUID
                Presets.objects.create(
                    id=setting_id,
                    id_user_id=user.id,
                    model=installed_models[0]['name'],
                    language = 'en',
                    temperature = 0.5,
                    max_token_output = 2048,
                )
                
                # Log the user in
                login(request, user)
                
                # Redirect to home page after successful registration
                return redirect('home')
                
            except ValidationError as e:
                form_errors['__all__'] = list(e.messages)
        
        # If we got here, there were errors
        return render(
            request,
            'app/register.html',
            {
                'title': 'Register',
                'year': datetime.now().year,
                'form': {
                    'username': {'value': username, 'errors': form_errors.get('username', [])},
                    'email': {'value': email, 'errors': form_errors.get('email', [])},
                    'password1': {'value': '', 'errors': form_errors.get('password1', [])},
                    'errors': form_errors.get('__all__', [])
                }
            }
        )
    
    # For GET requests, display empty form
    return render(
        request,
        'app/register.html',
        {
            'title': 'Register',
            'year': datetime.now().year,
            'form': {}
        }
    )
    
# Add this function to handle not found errors

def not_found(request, exception=None, error_type=None):
    """Renders the not found page with context-specific messages."""
    assert isinstance(request, HttpRequest)
    
    # Check if this is a chat-specific not found error
    if error_type == 'chat_not_found' or (request.path.startswith('/chat/') and not exception):
        title = "Chat Not Found"
        message = "We couldn't find the chat you're looking for."
        error_type = 'chat_not_found'
    else:
        title = "Page Not Found"
        message = "Oops! The page you're looking for doesn't exist."
        error_type = 'general_not_found'
    
    context = {
        'title': title,
        'message': message,
        'error_type': error_type,
        'year': datetime.now().year,
    }
    
    # Return with 404 status code
    return render(request, 'app/not_found.html', context, status=404)

