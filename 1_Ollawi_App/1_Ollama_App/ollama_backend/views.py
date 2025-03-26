from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import ollama
import os
import uuid
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from ollama_backend.models import Presets, Chats, DetailChats
from django.contrib.auth.models import User

def generate_id(prefix, length):
    """Generate a unique ID with given prefix and length"""
    unique_id = str(uuid.uuid4()).replace('-', '')[:length]
    return f"{prefix}-{unique_id}"

def auto_generate_title(prompt_input):
    """Generate a title from the first few words of the prompt"""
    words = prompt_input.strip().split()
    if len(words) <= 5:
        title = prompt_input[:50]
    else:
        title = ' '.join(words[:5]) + '...'
    return title[:50]  # Limit to 50 chars for title

def get_response_type(response_text):
    """Determine the type of response based on content"""
    if "```" in response_text:
        return "code"
    elif "<img" in response_text or "![" in response_text:
        return "image"
    elif "<table>" in response_text or "|--" in response_text:
        return "table"
    elif "$$" in response_text or "$" in response_text:
        return "math formula"
    else:
        return "string"

# Buat function bernama ollama_response_test yang menerima request dengan method POST dan mengembalikan response berupa JSON sederhana
@csrf_exempt
def ollama_response_test(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payload_input = data.get('payload_input', '')
            # Use the ollama package to process the payload_input
            ollama_response = ollama.chat(model="deepseek-r1:1.5b", messages=[{"role": "user", "content": payload_input}])
            # Extract the response text from the ChatResponse object
            response_text = ollama_response['message']['content']  # Extract the actual content
            response_data = {
                "status_code": "200",
                "message": response_text
            }
            return JsonResponse(response_data, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"status_code": "400", "message": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# Buat function bernama ollama_check yang menerima request dengan method GET dan mengembalikan response berupa JSON yang berisi model yang sudah diinstall di komputer melalui aplikasi Ollama
@csrf_exempt
def ollama_check(request):
    if request.method == 'GET':
        try:
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
            
            response_data = {
                "status_code": "200",
                "message": "Success",
                "installed_models": installed_models
            }
            return JsonResponse(response_data, status=200)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# Helper function to save files
def save_files(files, id_chat):
    folder_path = f"D:/karir/work/ollama_outputs/{id_chat}"
    os.makedirs(folder_path, exist_ok=True)
    for file in files:
        file_path = os.path.join(folder_path, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

@csrf_exempt
def ollama_presets(request):
    if request.method == 'GET':
        try:
            # Get all presets from the database
            presets_list = Presets.objects.all()
            
            # Format the presets for the response
            presets_data = []
            for preset in presets_list:
                presets_data.append({
                    "id": preset.id,
                    "name": preset.call_name,
                    "model": preset.model,
                    "language": preset.language,
                    "temperature": preset.temperature,
                    "max_token_output": preset.max_token_output,
                    "what_do": preset.what_do,
                    "instructions": preset.instructions,
                    "traits": preset.traits
                })
            
            response_data = {
                "status_code": "200",
                "message": "Success",
                "presets": presets_data
            }
            return JsonResponse(response_data, status=200)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# Route 1: Mengunggah prompt campuran ke AI secara lokal
@csrf_exempt
def ollama_post(request):
    if request.method == 'POST':
        try:
            # Parse request data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                prompt_input = data.get('prompt_input')
                preset_id = data.get('preset_id')
            else:
                prompt_input = request.POST.get('prompt_input')
                preset_id = request.POST.get('preset_id')
            
            files = request.FILES.getlist('files') if hasattr(request, 'FILES') else []

            # Validate required fields
            if not prompt_input:
                return JsonResponse({"status_code": "400", "message": "prompt_input is required"}, status=400)
            
            if not preset_id:
                return JsonResponse({"status_code": "400", "message": "preset_id is required"}, status=400)

            # Get preset data
            try:
                preset = Presets.objects.get(id=preset_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status_code": "404", "message": "Preset not found"}, status=404)

            # Get current user (assuming authentication is implemented)
            # For demo purposes, use the first user or create one if none exists
            user = None
            try:
                user = request.user if request.user.is_authenticated else User.objects.first()
                if not user:
                    # Create a default user if none exists
                    user = User.objects.create_user(username='default_user', password='password')
            except:
                return JsonResponse({"status_code": "500", "message": "User authentication error"}, status=500)
            
            # Use the ollama package to process the prompt_input
            model_name = preset.model or "deepseek-r1:1.5b"
            
            # Generate chat ID and detail ID
            chat_id = generate_id("chat", 12)
            detail_id_for_question = generate_id("detail-question", 15)
            
            # Auto-generate title from prompt
            title = auto_generate_title(prompt_input)
            
            # Save to database
            with transaction.atomic():
                # Create new chat
                chat = Chats.objects.create(
                    id=chat_id,
                    id_user=user,
                    id_presets=preset,
                    title=title,
                )
                
                # Create first detail chat
                DetailChats.objects.create(
                    id=detail_id_for_question,
                    id_user=user,
                    id_chat=chat,
                    type_option="Input",
                    text=prompt_input,
                    model=model_name,
                    language=preset.language,
                    temperature=preset.temperature,
                    max_token_output=preset.max_token_output,
                    is_string_only=preset.is_string_only,
                    is_code_file_only=preset.is_code_file_only,
                    is_multimedia_file_only=preset.is_multimedia_file_only,
                    is_musical_notes_only=preset.is_musical_notes_only,
                    is_table_only=preset.is_table_only,
                    include_math_formula=preset.include_math_formula,
                    include_musical_notes=preset.include_musical_notes,
                    include_code_file=preset.include_code_file,
                    include_multimedia_file=preset.include_multimedia_file,
                    include_chart=preset.include_chart,
                    include_table=preset.include_table,
                    call_name=preset.call_name,
                    what_do=preset.what_do,
                    instructions=preset.instructions,
                    traits=preset.traits
                )
            
            ollama_response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt_input}])
            response_text = ollama_response['message']['content']

            # Save files if any
            if files:
                save_files(files, chat_id)

            detail_id_for_answer = generate_id("detail-answer", 17)
            
            # Save to database
            with transaction.atomic():
                # Create first detail chat
                DetailChats.objects.create(
                    id=detail_id_for_answer,
                    id_user=user,
                    id_chat=chat,
                    type_option="Output",
                    text=response_text,
                    model=model_name,
                    language=preset.language,
                    temperature=preset.temperature,
                    max_token_output=preset.max_token_output,
                    is_string_only=preset.is_string_only,
                    is_code_file_only=preset.is_code_file_only,
                    is_multimedia_file_only=preset.is_multimedia_file_only,
                    is_musical_notes_only=preset.is_musical_notes_only,
                    is_table_only=preset.is_table_only,
                    include_math_formula=preset.include_math_formula,
                    include_musical_notes=preset.include_musical_notes,
                    include_code_file=preset.include_code_file,
                    include_multimedia_file=preset.include_multimedia_file,
                    include_chart=preset.include_chart,
                    include_table=preset.include_table,
                    call_name=preset.call_name,
                    what_do=preset.what_do,
                    instructions=preset.instructions,
                    traits=preset.traits
                )

            # Prepare response
            # response_type = get_response_type(response_text)
            response_data = {
                "status_code": "200",
                "message": "Success",
                "results": [
                    {
                        "id": detail_id_for_answer,
                        "id_chat": chat_id,
                        "type": "string",
                        "message": response_text
                    }
                ]
            }
            return JsonResponse(response_data, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"status_code": "400", "message": "Invalid JSON"}, status=400)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# Route 2: Mengunggah prompt ke AI dengan chat yang sudah ada
@csrf_exempt
def ollama_post_existing(request, id_chat):
    if request.method == 'POST':
        try:
            # Parse request data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                prompt_input = data.get('prompt_input')
                preset_id = data.get('preset_id')
            else:
                prompt_input = request.POST.get('prompt_input')
                preset_id = request.POST.get('preset_id')
            
            files = request.FILES.getlist('files') if hasattr(request, 'FILES') else []

            # Validate required fields
            if not prompt_input:
                return JsonResponse({"status_code": "400", "message": "prompt_input is required"}, status=400)
            
            if not preset_id:
                return JsonResponse({"status_code": "400", "message": "preset_id is required"}, status=400)

            # Verify chat exists
            try:
                chat = Chats.objects.get(id=id_chat)
            except ObjectDoesNotExist:
                return JsonResponse({"status_code": "404", "message": "Chat not found"}, status=404)

            # Get preset data
            try:
                preset = Presets.objects.get(id=preset_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status_code": "404", "message": "Preset not found"}, status=404)

            # Get current user
            user = None
            try:
                user = request.user if request.user.is_authenticated else User.objects.first()
                if not user:
                    # Create a default user if none exists
                    user = User.objects.create_user(username='default_user', password='password')
            except:
                return JsonResponse({"status_code": "500", "message": "User authentication error"}, status=500)
                
            # Use the ollama package to process the prompt_input
            model_name = preset.model or "deepseek-r1:1.5b"
            
            # Generate ID for the new detail chat
            detail_id_question = generate_id("detail-question", 15)
            
            DetailChats.objects.create(
                id=detail_id_question,
                id_user=user,
                id_chat=chat,
                type_option="Input",
                text=prompt_input,
                model=model_name,
                language=preset.language,
                temperature=preset.temperature,
                max_token_output=preset.max_token_output,
                is_string_only=preset.is_string_only,
                is_code_file_only=preset.is_code_file_only,
                is_multimedia_file_only=preset.is_multimedia_file_only,
                is_musical_notes_only=preset.is_musical_notes_only,
                is_table_only=preset.is_table_only,
                include_math_formula=preset.include_math_formula,
                include_musical_notes=preset.include_musical_notes,
                include_code_file=preset.include_code_file,
                include_multimedia_file=preset.include_multimedia_file,
                include_chart=preset.include_chart,
                include_table=preset.include_table,
                call_name=preset.call_name,
                what_do=preset.what_do,
                instructions=preset.instructions,
                traits=preset.traits
            )
            ollama_response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt_input}])
            response_text = ollama_response['message']['content']

            # Save files if any
            if files:
                save_files(files, id_chat)

            detail_id_answer = generate_id("detail-answer", 17)
            # Save to database - only DetailChats
            detail_chat = DetailChats.objects.create(
                id=detail_id_answer,
                id_user=user,
                id_chat=chat,
                type_option="Output",
                text=response_text,
                model=model_name,
                language=preset.language,
                temperature=preset.temperature,
                max_token_output=preset.max_token_output,
                is_string_only=preset.is_string_only,
                is_code_file_only=preset.is_code_file_only,
                is_multimedia_file_only=preset.is_multimedia_file_only,
                is_musical_notes_only=preset.is_musical_notes_only,
                is_table_only=preset.is_table_only,
                include_math_formula=preset.include_math_formula,
                include_musical_notes=preset.include_musical_notes,
                include_code_file=preset.include_code_file,
                include_multimedia_file=preset.include_multimedia_file,
                include_chart=preset.include_chart,
                include_table=preset.include_table,
                call_name=preset.call_name,
                what_do=preset.what_do,
                instructions=preset.instructions,
                traits=preset.traits
            )

            # Update the chat's updated_at field
            chat.save()  # This updates the updated_at field automatically
            
            # Prepare response
            # response_type = get_response_type(response_text)
            
            response_data = {
                "status_code": "200",
                "message": "Success",
                "results": [
                    {
                        "id": detail_id_answer,
                        "id_chat": id_chat,
                        "type": "string",
                        "message": response_text
                    }
                ]
            }
            return JsonResponse(response_data, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"status_code": "400", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# Route 3: Melihat semua riwayat chat
@csrf_exempt
def ollama_chats(request):
    if request.method == 'GET':
        try:
            # Get all chats with their details
            chats = Chats.objects.all().select_related('id_group').prefetch_related('detail_chats')
            
            histories = []
            for chat in chats:
                # Get group name if exists
                group_name = chat.id_group.title if chat.id_group else None
                
                # Get all detail chats for this chat
                detail_chats = chat.detail_chats.all().order_by('created_at')
                
                # Format results
                results = []
                for detail in detail_chats:
                    # Add each message only once with its proper type
                    type_prefix = "detail-question" if detail.type_option == "Input" else "detail-answer"
                    results.append({
                        "id": detail.id,
                        "type": detail.type_option,
                        "type_prefix": type_prefix,
                        "message": detail.text
                    })
                
                # Add this chat to histories
                histories.append({
                    "id_chat": chat.id,
                    "title": chat.title,
                    "group": group_name,
                    "results": results
                })
            
            response_data = {
                "status_code": "200",
                "message": "Success",
                "histories": histories
            }
            return JsonResponse(response_data, status=200)
            
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)

# filepath: d:\Dicoding_Indonesia_files\python\others\1_Ollama_App\1_Ollama_App\ollama_backend\views.py

# Route to get chat details
@csrf_exempt
def ollama_chat_detail(request, id_chat):
    if request.method == 'GET':
        try:
            # Get chat with details
            chat = Chats.objects.get(id=id_chat)
            
            # Check if user has permission to access this chat
            if request.user.is_authenticated and chat.id_user != request.user:
                return JsonResponse({"status_code": "403", "message": "Access denied"}, status=403)
            
            # Get all details for this chat
            detail_chats = DetailChats.objects.filter(id_chat=chat).order_by('created_at')
            
            details = []
            for detail in detail_chats:
                details.append({
                    "id": detail.id,
                    "type_option": detail.type_option,
                    "text": detail.text,
                    "created_at": detail.created_at.isoformat() if detail.created_at else None
                })
            
            response_data = {
                "status_code": "200",
                "message": "Success",
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "details": details
            }
            return JsonResponse(response_data, status=200)
            
        except ObjectDoesNotExist:
            return JsonResponse({"status_code": "404", "message": "Chat not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                # First delete all details associated with this chat
                cursor.execute("DELETE FROM ollama_backend_detailchats WHERE id_chat_id = %s", [id_chat])
                # Then delete the chat
                cursor.execute("DELETE FROM ollama_backend_chats WHERE id = %s", [id_chat])
            return JsonResponse({"status_code": "200", "message": "No Content"}, status=200)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)
    
# Add this function to update chat title
@csrf_exempt
def ollama_chat_update_title(request, id_chat):
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            new_title = data.get('title')
            
            if not new_title:
                return JsonResponse({"status_code": "400", "message": "Title is required"}, status=400)
            
            # Get the chat
            chat = Chats.objects.get(id=id_chat)
            
            # Check if user has permission
            if request.user.is_authenticated and chat.id_user != request.user:
                return JsonResponse({"status_code": "403", "message": "Access denied"}, status=403)
            
            # Update the title
            chat.title = new_title
            chat.save()
            
            return JsonResponse({
                "status_code": "200", 
                "message": "Title updated successfully",
                "id": chat.id,
                "title": chat.title
            }, status=200)
            
        except ObjectDoesNotExist:
            return JsonResponse({"status_code": "404", "message": "Chat not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"status_code": "400", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"status_code": "500", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status_code": "405", "message": "Method not allowed"}, status=405)