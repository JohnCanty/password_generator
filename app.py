"""
Flask-based Password Generator Web Application
Cryptographically secure password generation using Python's secrets module
"""

from flask import Flask, render_template, request, jsonify
import secrets
import string
import re

app = Flask(__name__)

# Constants for character sets
UPPERCASE = string.ascii_uppercase
LOWERCASE = string.ascii_lowercase
DIGITS = string.digits
AMBIGUOUS_CHARS = '0Ol1I'


def sanitize_length(length_str):
    """
    Sanitize and validate password length input.
    
    Args:
        length_str: String representation of password length
        
    Returns:
        int: Validated password length (between 4 and 128)
    """
    try:
        length = int(length_str)
        # Clamp length between reasonable bounds
        if length < 4:
            return 4
        elif length > 128:
            return 128
        return length
    except (ValueError, TypeError):
        return 8  # Default to 8 if invalid input


def sanitize_special_chars(special_chars_str):
    """
    Sanitize special characters input.
    
    Args:
        special_chars_str: Comma-separated string of special characters
        
    Returns:
        str: Sanitized string of special characters
    """
    if not special_chars_str or not isinstance(special_chars_str, str):
        return "!@#*"  # Default special characters
    
    # Remove whitespace and split by comma
    chars = [char.strip() for char in special_chars_str.split(',')]
    # Filter out empty strings and join
    chars = ''.join([c for c in chars if c])
    
    # Limit to printable ASCII characters (excluding alphanumeric)
    sanitized = ''.join([c for c in chars if c in string.punctuation])
    
    # If nothing valid remains, use default
    return sanitized if sanitized else "!@#*"


def calculate_password_strength(password, length):
    """
    Calculate password strength based on entropy and composition.
    
    Args:
        password: Generated password string
        length: Length of the password
        
    Returns:
        str: Strength rating ('weak', 'medium', 'strong')
    """
    # Check character diversity
    has_upper = any(c in UPPERCASE for c in password)
    has_lower = any(c in LOWERCASE for c in password)
    has_digit = any(c in DIGITS for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    diversity = sum([has_upper, has_lower, has_digit, has_special])
    
    # Calculate strength based on length and diversity
    if length >= 16 and diversity >= 3:
        return 'strong'
    elif length >= 12 and diversity >= 3:
        return 'strong'
    elif length >= 10 and diversity >= 2:
        return 'medium'
    elif length >= 8 and diversity >= 2:
        return 'medium'
    else:
        return 'weak'


def generate_password(length, special_chars, exclude_ambiguous):
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Desired password length
        special_chars: String of allowed special characters
        exclude_ambiguous: Boolean to exclude ambiguous characters
        
    Returns:
        tuple: (password string, strength rating)
    """
    # Build character pool
    char_pool = UPPERCASE + LOWERCASE + DIGITS + special_chars
    
    # Remove ambiguous characters if requested
    if exclude_ambiguous:
        char_pool = ''.join([c for c in char_pool if c not in AMBIGUOUS_CHARS])
    
    # Ensure we have at least some characters to work with
    if not char_pool:
        char_pool = LOWERCASE + DIGITS  # Fallback to basic set
    
    # Generate password using secrets module for cryptographic security
    # This is suitable for security-sensitive applications
    password = ''.join(secrets.choice(char_pool) for _ in range(length))
    
    # Calculate strength
    strength = calculate_password_strength(password, length)
    
    return password, strength


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def api_generate_password():
    """
    API endpoint for password generation.
    
    Expected JSON payload:
    {
        "length": int,
        "special_chars": str (comma-separated),
        "exclude_ambiguous": bool
    }
    
    Returns:
        JSON response with password and strength
    """
    try:
        data = request.get_json()
        
        # Sanitize inputs
        length = sanitize_length(data.get('length', 8))
        special_chars = sanitize_special_chars(data.get('special_chars', '!,@,#,*'))
        exclude_ambiguous = data.get('exclude_ambiguous', True)
        
        # Generate password
        password, strength = generate_password(length, special_chars, exclude_ambiguous)
        
        return jsonify({
            'success': True,
            'password': password,
            'strength': strength,
            'length': length
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    # For development only - use Gunicorn in production
    app.run(debug=False, host='0.0.0.0', port=2048)
