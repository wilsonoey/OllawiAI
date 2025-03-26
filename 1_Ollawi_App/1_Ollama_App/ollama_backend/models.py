from django.db import models
import uuid
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django_mysql.models import EnumField

# Create your models here.
class Presets(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=16)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    model = models.CharField(max_length=255)
    language = models.CharField(max_length=255, null=True, blank=True)
    temperature = models.FloatField(validators=[MaxValueValidator(1)])
    max_token_output = models.PositiveIntegerField(validators=[MaxValueValidator(2048)])
    is_string_only = models.BooleanField(default=False)
    is_code_file_only = models.BooleanField(default=False)
    is_multimedia_file_only = models.BooleanField(default=False)
    is_musical_notes_only = models.BooleanField(default=False)
    is_table_only = models.BooleanField(default=False)
    include_math_formula = models.BooleanField(default=False)
    include_musical_notes = models.BooleanField(default=False)
    include_code_file = models.BooleanField(default=False)
    include_multimedia_file = models.BooleanField(default=False)
    include_chart = models.BooleanField(default=False)
    include_table = models.BooleanField(default=False)
    call_name = models.CharField(max_length=255, default='Default Preset', null=True, blank=True)
    what_do = models.CharField(max_length=255, default='', null=True, blank=True)
    instructions = models.TextField(default='', null=True, blank=True)
    apply_for_new_chat_only = models.BooleanField(default=False)
    traits = models.TextField(default='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Plan_Directories(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=24)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    directory = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Group_Chat(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=24)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Chats(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=32)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    id_presets = models.ForeignKey(Presets, on_delete=models.CASCADE, related_name='chats')
    id_group = models.ForeignKey(Group_Chat, on_delete=models.CASCADE, related_name='chats', null=True, blank=True)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class DetailChats(models.Model):
    class TypeOptions(models.TextChoices):
        INPUT = "Input"
        OUTPUT = "Output"

    id = models.CharField(primary_key=True, editable=False, max_length=64)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    id_chat = models.ForeignKey(Chats, on_delete=models.CASCADE, related_name='detail_chats')
    type_option = EnumField(choices=TypeOptions.choices)
    text = models.TextField()
    model = models.CharField(max_length=255)
    language = models.CharField(max_length=255, null=True, blank=True)
    temperature = models.FloatField(validators=[MaxValueValidator(1)])
    max_token_output = models.PositiveIntegerField(validators=[MaxValueValidator(2048)])
    is_string_only = models.BooleanField(default=False)
    is_code_file_only = models.BooleanField(default=False)
    is_multimedia_file_only = models.BooleanField(default=False)
    is_musical_notes_only = models.BooleanField(default=False)
    is_table_only = models.BooleanField(default=False)
    include_string = models.BooleanField(default=True)
    include_math_formula = models.BooleanField(default=False)
    include_musical_notes = models.BooleanField(default=False)
    include_code_file = models.BooleanField(default=False)
    include_multimedia_file = models.BooleanField(default=False)
    include_chart = models.BooleanField(default=False)
    include_table = models.BooleanField(default=False)
    call_name = models.CharField(max_length=255, default='Default Preset', null=True, blank=True)
    what_do = models.CharField(max_length=255, default='', null=True, blank=True)
    instructions = models.TextField(default='', null=True, blank=True)
    traits = models.TextField(default='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    id = models.CharField(primary_key=True, editable=False, max_length=64)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    id_chat = models.ForeignKey(DetailChats, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField(validators=[MaxValueValidator(5)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Setting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    font_size = models.PositiveIntegerField(validators=[MaxValueValidator(100)])
    show_word_count = models.BooleanField(default=False)
    show_message_token_count = models.BooleanField(default=False)
    show_message_token_usage = models.BooleanField(default=False)
    show_model_name = models.BooleanField(default=False)
    show_message_timestamp = models.BooleanField(default=False)
    show_first_token_latency = models.BooleanField(default=False)
    spell_check = models.BooleanField(default=False)
    is_dark_mode = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
