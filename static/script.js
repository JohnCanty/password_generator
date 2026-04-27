// DOM Elements
const passwordDisplay = document.getElementById('passwordDisplay');
const copyBtn = document.getElementById('copyBtn');
const generateBtn = document.getElementById('generateBtn');
const passwordLength = document.getElementById('passwordLength');
const specialChars = document.getElementById('specialChars');
const generateLocally = document.getElementById('generateLocally');
const generationModeHelp = document.getElementById('generationModeHelp');
const excludeAmbiguous = document.getElementById('excludeAmbiguous');
const strengthIndicator = document.getElementById('strengthIndicator');
const strengthFill = document.getElementById('strengthFill');
const strengthText = document.getElementById('strengthText');
const quickSelectButtons = document.querySelectorAll('.btn-quick');

// Shared constants
const DEFAULT_SPECIAL_CHARS = '!@#*';
const MIN_PASSWORD_LENGTH = Number.parseInt(passwordLength.min, 10) || 4;
const MAX_PASSWORD_LENGTH = Number.parseInt(passwordLength.max, 10) || 128;
const MAX_SPECIAL_CHARS_INPUT = Number.parseInt(
    specialChars.getAttribute('maxlength'),
    10
) || 128;
const AMBIGUOUS_CHARS = new Set('0Ol1I');
const ASCII_PUNCTUATION = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";

// State
let currentPassword = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setActiveQuickButton(sanitizeLength(passwordLength.value));
    updateGenerationModeHelp();
});

/**
 * Set up all event listeners.
 */
function setupEventListeners() {
    generateBtn.addEventListener('click', generatePassword);
    copyBtn.addEventListener('click', copyToClipboard);
    generateLocally.addEventListener('change', updateGenerationModeHelp);

    quickSelectButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            const length = Number.parseInt(event.currentTarget.dataset.length, 10);
            passwordLength.value = sanitizeLength(length);
            setActiveQuickButton(length);
        });
    });

    passwordLength.addEventListener('input', (event) => {
        const length = sanitizeLength(event.target.value);
        setActiveQuickButton(length);
    });

    [passwordLength, specialChars].forEach((input) => {
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                generatePassword();
            }
        });
    });
}

/**
 * Set active state for quick select buttons.
 */
function setActiveQuickButton(length) {
    quickSelectButtons.forEach((button) => {
        const buttonLength = Number.parseInt(button.dataset.length, 10);
        button.classList.toggle('active', buttonLength === length);
    });
}

/**
 * Update the help text for the active generation mode.
 */
function updateGenerationModeHelp() {
    generationModeHelp.textContent = generateLocally.checked
        ? 'Local mode uses the Web Crypto API and keeps password generation in this browser.'
    : 'Server mode is the default. The password is generated on the server and returned over a same-origin request.';
}

/**
 * Collect, sanitize, and normalize form values before generation.
 */
function collectGenerationOptions() {
    const length = sanitizeLength(passwordLength.value);
    passwordLength.value = length;

    return {
        length,
        specialChars: sanitizeSpecialChars(specialChars.value),
        excludeAmbiguous: excludeAmbiguous.checked,
    };
}

/**
 * Generate a password either locally or via the server API.
 */
async function generatePassword() {
    try {
        generateBtn.disabled = true;
        generateBtn.textContent = generateLocally.checked
            ? 'Generating Locally...'
            : 'Generating...';

        const options = collectGenerationOptions();
        const result = generateLocally.checked
            ? generatePasswordLocally(options)
            : await generatePasswordOnServer(options);

        currentPassword = result.password;
        displayPassword(result.password);
        updateStrengthIndicator(result.strength);
        copyBtn.disabled = false;
    } catch (error) {
        console.error('Password generation failed:', error);
        showToast(error.message || 'Failed to generate password. Please try again.', 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Password';
    }
}

/**
 * Request a server-generated password from the Flask API.
 */
async function generatePasswordOnServer(options) {
    const response = await fetch('/api/generate', {
        method: 'POST',
        cache: 'no-store',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            length: options.length,
            special_chars: options.specialChars,
            exclude_ambiguous: options.excludeAmbiguous,
        }),
    });

    let result;
    try {
        result = await response.json();
    } catch (error) {
        throw new Error('Server returned an invalid response.');
    }

    if (!response.ok || !result.success) {
        throw new Error(result.error || 'Password generation failed.');
    }

    return result;
}

/**
 * Generate a password locally using the Web Crypto API.
 */
function generatePasswordLocally(options) {
    if (!window.crypto || typeof window.crypto.getRandomValues !== 'function') {
        throw new Error('This browser does not support secure local generation.');
    }

    const charPool = buildCharacterPool(options.specialChars, options.excludeAmbiguous);
    let password = '';

    for (let index = 0; index < options.length; index += 1) {
        password += charPool[getSecureRandomIndex(charPool.length)];
    }

    return {
        success: true,
        password,
        strength: calculatePasswordStrength(password, options.length),
        length: options.length,
        mode: 'local',
    };
}

/**
 * Build the available character pool for either generation mode.
 */
function buildCharacterPool(specialCharacters, excludeAmbiguousCharacters) {
    let pool =
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
        'abcdefghijklmnopqrstuvwxyz' +
        '0123456789' +
        specialCharacters;

    if (excludeAmbiguousCharacters) {
        pool = [...pool].filter((character) => !AMBIGUOUS_CHARS.has(character)).join('');
    }

    return pool || 'abcdefghijklmnopqrstuvwxyz0123456789';
}

/**
 * Return a uniformly distributed secure index within the requested range.
 */
function getSecureRandomIndex(maxExclusive) {
    if (!Number.isInteger(maxExclusive) || maxExclusive <= 0) {
        throw new Error('Invalid secure random range requested.');
    }

    const maxUint32 = 0x100000000;
    const cutoff = Math.floor(maxUint32 / maxExclusive) * maxExclusive;
    const buffer = new Uint32Array(1);

    do {
        window.crypto.getRandomValues(buffer);
    } while (buffer[0] >= cutoff);

    return buffer[0] % maxExclusive;
}

/**
 * Clamp password length to the values enforced by the server.
 */
function sanitizeLength(lengthValue) {
    const parsedLength = Number.parseInt(lengthValue, 10);
    if (Number.isNaN(parsedLength)) {
        return 8;
    }

    return Math.min(Math.max(parsedLength, MIN_PASSWORD_LENGTH), MAX_PASSWORD_LENGTH);
}

/**
 * Keep only printable ASCII punctuation and bound the input size.
 */
function sanitizeSpecialChars(value) {
    if (typeof value !== 'string') {
        return DEFAULT_SPECIAL_CHARS;
    }

    const trimmedValue = value.trim();
    if (!trimmedValue || trimmedValue.length > MAX_SPECIAL_CHARS_INPUT) {
        return DEFAULT_SPECIAL_CHARS;
    }

    const joinedValue = trimmedValue
        .split(',')
        .map((part) => part.trim())
        .join('');

    const sanitizedChars = [];
    const seenChars = new Set();
    for (const character of joinedValue) {
        if (ASCII_PUNCTUATION.includes(character) && !seenChars.has(character)) {
            sanitizedChars.push(character);
            seenChars.add(character);
        }
    }

    return sanitizedChars.join('') || DEFAULT_SPECIAL_CHARS;
}

/**
 * Estimate password strength using the same rules as the server.
 */
function calculatePasswordStrength(password, length) {
    const hasUpper = [...password].some((character) => /[A-Z]/.test(character));
    const hasLower = [...password].some((character) => /[a-z]/.test(character));
    const hasDigit = [...password].some((character) => /[0-9]/.test(character));
    const hasSpecial = [...password].some((character) => ASCII_PUNCTUATION.includes(character));
    const diversity = [hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;

    if (length >= 12 && diversity >= 3) {
        return 'strong';
    }
    if (length >= 10 && diversity >= 2) {
        return 'medium';
    }
    if (length >= 8 && diversity >= 2) {
        return 'medium';
    }
    return 'weak';
}

/**
 * Display password in the UI without using HTML injection.
 */
function displayPassword(password) {
    passwordDisplay.classList.add('has-password');
    passwordDisplay.textContent = password;
}

/**
 * Update the strength indicator styles and label.
 */
function updateStrengthIndicator(strength) {
    strengthIndicator.classList.remove('is-hidden');
    strengthFill.classList.remove('weak', 'medium', 'strong');
    strengthText.classList.remove('weak', 'medium', 'strong');
    strengthFill.classList.add(strength);
    strengthText.classList.add(strength);
    strengthText.textContent = strength.charAt(0).toUpperCase() + strength.slice(1);
}

/**
 * Copy the current password to the clipboard.
 */
async function copyToClipboard() {
    if (!currentPassword) {
        return;
    }

    try {
        await navigator.clipboard.writeText(currentPassword);
        showToast('Password copied to clipboard!');
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
        console.error('Failed to copy password:', error);
        fallbackCopyToClipboard(currentPassword);
    }
}

/**
 * Fallback copy method for browsers that do not support the Clipboard API.
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
        showToast('Failed to copy password.', 'error');
    }

    document.body.removeChild(textArea);
}

/**
 * Show a transient toast notification.
 */
function showToast(message, type = 'success') {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;

    if (type === 'error') {
        toast.style.background = '#ef4444';
    }

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}
