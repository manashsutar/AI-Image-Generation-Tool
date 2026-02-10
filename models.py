
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class ChatSession(TimeStampedModel):
    """
    Chat Session Model
    Tracks conversation sessions
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True,
        verbose_name=_('user'),
        help_text=_('User who owns this session (null for anonymous)')
    )
    
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        unique=True,
        help_text=_('Unique session identifier')
    )
    
    title = models.CharField(
        _('session title'),
        max_length=200,
        blank=True,
        help_text=_('Auto-generated from first message')
    )
    
    context_page = models.CharField(
        _('context page'),
        max_length=255,
        blank=True,
        help_text=_('Page where chat was initiated')
    )
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether session is currently active')
    )
    
    ended_at = models.DateTimeField(
        _('ended at'),
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'chat_sessions'
        verbose_name = _('Chat Session')
        verbose_name_plural = _('Chat Sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.title or 'Untitled'}"
    
    @property
    def message_count(self):
        """Count of messages in this session"""
        return self.messages.count()
    
    def end_session(self):
        """End the chat session"""
        from django.utils import timezone
        self.is_active = False
        self.ended_at = timezone.now()
        self.save()


class ChatMessage(TimeStampedModel):
    """
    Chat Message Model
    Individual messages in a conversation
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('session')
    )
    
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES,
        help_text=_('Who sent this message')
    )
    
    content = models.TextField(
        _('message content'),
        help_text=_('The actual message text')
    )
    
    context_data = models.JSONField(
        _('context data'),
        default=dict,
        blank=True,
        help_text=_('Additional context (page, service, etc.)')
    )
    
    response_time_ms = models.PositiveIntegerField(
        _('response time (ms)'),
        null=True,
        blank=True,
        help_text=_('Time taken to generate response')
    )
    
    tokens_used = models.PositiveIntegerField(
        _('tokens used'),
        null=True,
        blank=True,
        help_text=_('Number of tokens in response')
    )
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ChatFeedback(TimeStampedModel):
    """
    Chat Feedback Model
    User feedback on AI responses
    """
    RATING_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
    ]
    
    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name=_('message')
    )
    
    rating = models.CharField(
        _('rating'),
        max_length=10,
        choices=RATING_CHOICES
    )
    
    comment = models.TextField(
        _('feedback comment'),
        blank=True,
        help_text=_('Optional feedback comment')
    )
    
    class Meta:
        db_table = 'chat_feedback'
        verbose_name = _('Chat Feedback')
        verbose_name_plural = _('Chat Feedback')
    
    def __str__(self):
        return f"{self.rating} - {self.message.session.session_id}"
