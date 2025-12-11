import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import EmailStr
from fastapi_mail import ConnectionConfig, MessageSchema
from fastapi_mail.errors import ConnectionErrors

# Import the functions under test
from src.services.email import send_verification_email, send_password_reset_email

@pytest.mark.asyncio
@patch('src.services.email.config')
@patch('src.services.email.create_email_token')
async def test_send_verification_email_success(mock_create_token, mock_config):
    """Tests successful execution of send_verification_email."""
    
    mock_create_token.return_value = "mocked_verification_token"
    mock_fm_instance = AsyncMock()
    
    with patch('src.services.email.FastMail', return_value=mock_fm_instance):
        
        await send_verification_email(
            email="test@example.com", 
            username="testuser",
            host="http://localhost"
        )

        mock_fm_instance.send_message.assert_awaited_once()
        
        call_args = mock_fm_instance.send_message.call_args
        assert call_args.kwargs["template_name"] == "verify_email.html"
        
        message_schema: MessageSchema = call_args.args[0]
        assert message_schema.subject == "Confirm your email"
        # Check the expected formatted string: "{name} <{email}>"
        assert str(message_schema.recipients[0]) == "test <test@example.com>" 
        assert message_schema.template_body["username"] == "testuser"
        assert message_schema.template_body["token"] == "mocked_verification_token"


@pytest.mark.asyncio
@patch('src.services.email.config')
@patch('src.services.email.create_email_token')
async def test_send_verification_email_connection_error(mock_create_token, mock_config):
    """Tests handling of ConnectionErrors during email verification sending."""
    
    mock_create_token.return_value = "mocked_token"
    
    mock_fm_instance = AsyncMock()
    mock_fm_instance.send_message.side_effect = ConnectionErrors("SMTP connection refused")
    
    with patch('src.services.email.FastMail', return_value=mock_fm_instance):
        
        await send_verification_email(
            email="test@example.com",
            username="testuser",
            host="http://localhost"
        )
        
        mock_fm_instance.send_message.assert_awaited_once()


@pytest.mark.asyncio
@patch('src.services.email.config')
@patch('src.services.email.create_email_token')
async def test_send_password_reset_email_success(mock_create_token, mock_config):
    """Tests successful execution of send_password_reset_email."""
    
    mock_create_token.return_value = "mocked_reset_token"
    mock_fm_instance = AsyncMock()
    
    with patch('src.services.email.FastMail', return_value=mock_fm_instance):
        
        await send_password_reset_email(
            email="reset@example.com",
            username="resetuser",
            host="http://localhost"
        )
        
        mock_fm_instance.send_message.assert_awaited_once()
        
        call_args = mock_fm_instance.send_message.call_args
        assert call_args.kwargs["template_name"] == "reset_password.html"
        
        message_schema: MessageSchema = call_args.args[0]
        assert message_schema.subject == "Password reset"
        # Check the expected formatted string: "{name} <{email}>"
        assert str(message_schema.recipients[0]) == "reset <reset@example.com>" 
        assert message_schema.template_body["username"] == "resetuser"
        assert message_schema.template_body["token"] == "mocked_reset_token"


@pytest.mark.asyncio
@patch('src.services.email.config')
@patch('src.services.email.create_email_token')
async def test_send_password_reset_email_connection_error(mock_create_token, mock_config):
    """Tests handling of ConnectionErrors during password reset sending."""
    
    mock_create_token.return_value = "mocked_token"
    
    mock_fm_instance = AsyncMock()
    mock_fm_instance.send_message.side_effect = ConnectionErrors("SMTP connection failure")
    
    with patch('src.services.email.FastMail', return_value=mock_fm_instance):
        
        await send_password_reset_email(
            email="reset@example.com",
            username="resetuser",
            host="http://localhost"
        )
        
        mock_fm_instance.send_message.assert_awaited_once()