"""
AI Chatbot Views
"""

import time
import uuid
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import ChatSession, ChatMessage, ChatFeedback
from .services import get_chatbot


@require_POST
def chat_view(request):
    """
    Chat endpoint (AJAX)
    Handles incoming messages and returns AI responses
    """
    # Get request data
    message = request.POST.get('message', '').strip()
    session_id = request.POST.get('session_id', '')
    page_context = request.POST.get('page_context', '')
    
    # Validate
    if not message:
        return JsonResponse({
            'error': 'Message is required'
        }, status=400)
    
    # Get or create session
    if not session_id:
        session_id = str(uuid.uuid4())
    
    session, created = ChatSession.objects.get_or_create(
        session_id=session_id,
        defaults={
            'user': request.user if request.user.is_authenticated else None,
            'context_page': page_context,
        }
    )
    
    # Save user message
    user_message = ChatMessage.objects.create(
        session=session,
        role='user',
        content=message,
        context_data={'page': page_context}
    )
    
    # Get conversation history (last 10 messages)
    history_messages = ChatMessage.objects.filter(
        session=session
    ).order_by('created_at')[:10]
    
    conversation_history = [
        {'role': msg.role, 'content': msg.content}
        for msg in history_messages
    ]
    
    # Get AI response
    chatbot = get_chatbot()
    start_time = time.time()
    
    try:
        ai_response = chatbot.chat(
            message=message,
            conversation_history=conversation_history[:-1],  # Exclude current message
            context={'page': page_context}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Save assistant message
        assistant_message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_response,
            response_time_ms=response_time_ms
        )
        
        # Auto-generate session title from first message
        if created and not session.title:
            session.title = message[:50]
            session.save()
        
        return JsonResponse({
            'success': True,
            'response': ai_response,
            'session_id': session_id,
            'message_id': assistant_message.id,
            'response_time': response_time_ms
        })
    
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get response from AI',
            'detail': str(e)
        }, status=500)


@require_POST
def feedback_view(request):
    """
    Submit feedback on AI response (AJAX)
    """
    message_id = request.POST.get('message_id')
    rating = request.POST.get('rating')  # 'positive' or 'negative'
    comment = request.POST.get('comment', '')
    
    if not message_id or not rating:
        return JsonResponse({
            'error': 'message_id and rating are required'
        }, status=400)
    
    try:
        message = ChatMessage.objects.get(id=message_id, role='assistant')
        
        feedback, created = ChatFeedback.objects.update_or_create(
            message=message,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
    
    except ChatMessage.DoesNotExist:
        return JsonResponse({
            'error': 'Message not found'
        }, status=404)


def history_view(request):
    """
    Get chat history for current session (AJAX)
    """
    session_id = request.GET.get('session_id')
    
    if not session_id:
        return JsonResponse({
            'error': 'session_id is required'
        }, status=400)
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        history = [
            {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat()
            }
            for msg in messages
        ]
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'messages': history
        })
    
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'error': 'Session not found'
        }, status=404)


def health_check_view(request):
    """
    Check if AI chatbot service is available
    """
    chatbot = get_chatbot()
    is_healthy = chatbot.check_health()
    
    return JsonResponse({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'service': 'Ollama',
        'model': chatbot.model
    })
