// DOM Elements
const passwordDisplay = document.getElementById('passwordDisplay');
const copyBtn = document.getElementById('copyBtn');
const generateBtn = document.getElementById('generateBtn');
const passwordLength = document.getElementById('passwordLength');
const specialChars = document.getElementById('specialChars');
const excludeAmbiguous = document.getElementById('excludeAmbiguous');
const strengthIndicator = document.getElementById('strengthIndicator');
const strengthFill = document.getElementById('strengthFill');
const strengthText = document.getElementById('strengthText');
const quickSelectButtons = document.querySelectorAll('.btn-quick');

// State
let currentPassword = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setActiveQuickButton(8); // Set default active button
});

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Generate button
    generateBtn.addEventListener('click', generatePassword);

    // Copy button
    copyBtn.addEventListener('click', copyToClipboard);

    // Quick select buttons
    quickSelectButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const length = parseInt(e.target.dataset.length);
            passwordLength.value = length;
            setActiveQuickButton(length);
        });
    });

    // Password length input change
    passwordLength.addEventListener('input', (e) => {
        const length = parseInt(e.target.value);
        setActiveQuickButton(length);
    });

    // Enter key on inputs
    [passwordLength, specialChars].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                generatePassword();
            }
        });
    });
}

/**
 * Set active state for quick select button
 */
function setActiveQuickButton(length) {
    quickSelectButtons.forEach(btn => {
        const btnLength = parseInt(btn.dataset.length);
        if (btnLength === length) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

/**
 * Generate password via API
 */
async function generatePassword() {
    try {
        // Disable button during request
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        // Collect form data
        const data = {
            length: parseInt(passwordLength.value) || 8,
            special_chars: specialChars.value || '!,@,#,*',
            exclude_ambiguous: excludeAmbiguous.checked
        };

        // Make API request
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Display password
            currentPassword = result.password;
            displayPassword(result.password);
            
            // Update strength indicator
            updateStrengthIndicator(result.strength);
            
            // Enable copy button
            copyBtn.disabled = false;
        } else {
            showToast('Error generating password: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to generate password. Please try again.', 'error');
    } finally {
        // Re-enable button
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Password';
    }
}

/**
 * Display password in the UI
 */
function displayPassword(password) {
    passwordDisplay.classList.add('has-password');
    passwordDisplay.innerHTML = `<span>${escapeHtml(password)}</span>`;
}

/**
 * Update strength indicator
 */
function updateStrengthIndicator(strength) {
    strengthIndicator.style.display = 'block';
    
    // Remove all strength classes
    strengthFill.classList.remove('weak', 'medium', 'strong');
    strengthText.classList.remove('weak', 'medium', 'strong');
    
    // Add appropriate class
    strengthFill.classList.add(strength);
    strengthText.classList.add(strength);
    
    // Update text
    strengthText.textContent = strength.charAt(0).toUpperCase() + strength.slice(1);
}

/**
 * Copy password to clipboard
 */
async function copyToClipboard() {
    if (!currentPassword) return;

    try {
        await navigator.clipboard.writeText(currentPassword);
        showToast('Password copied to clipboard!');
        
        // Visual feedback
        copyBtn.textContent = '✓ Copied';
        setTimeout(() => {
            copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="1.5" fill="none"/>
                    <path d="M6 0h6a2 2 0 0 1 2 2v6" stroke="currentColor" stroke-width="1.5" fill="none"/>
                </svg>
                Copy
            `;
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        
        // Fallback for older browsers
        fallbackCopyToClipboard(currentPassword);
    }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('Password copied to clipboard!');
    } catch (error) {
        showToast('Failed to copy password', 'error');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    // Remove existing toast if any
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    
    if (type === 'error') {
        toast.style.background = '#ef4444';
    }

    document.body.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
