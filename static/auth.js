function showCard(id) {
    document.querySelectorAll('.auth-card').forEach(c => c.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}

function setLoading(btn, loadingText, normalText) {
    btn.disabled = true;
    btn.textContent = loadingText;
    btn.dataset.normalText = normalText;
}

function clearLoading(btn) {
    btn.disabled = false;
    btn.textContent = btn.dataset.normalText;
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function checkPasswordStrength(password, bar1, bar2, bar3) {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 8 && /[0-9]/.test(password) && /[a-z]/.test(password)) score++;
    if (password.length >= 8 && /[0-9]/.test(password) && /[A-Z]/.test(password) && /[a-z]/.test(password) && /[^A-Za-z0-9]/.test(password)) score++;

    const bars = [bar1, bar2, bar3];
    const colors = ['#ff3b30', '#ff9f0a', '#34c759'];
    bars.forEach((b, i) => { b.style.background = i < score ? colors[score - 1] : 'var(--border-subtle)'; });

    return score;
}

document.querySelectorAll('.auth-eye-btn').forEach(btn => {
    btn.addEventListener('mousedown', function(e) { e.preventDefault(); });
    btn.addEventListener('click', function() {
        const input = document.getElementById(this.dataset.target);
        const icon = this.querySelector('i');
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'ti ti-eye-off';
        } else {
            input.type = 'password';
            icon.className = 'ti ti-eye';
        }
        input.focus();
    });
});

// Theme Toggle — Single handler for all cards
document.querySelectorAll('#themeToggle').forEach(toggle => {
    toggle.addEventListener('click', function() {
        const isDark = document.body.classList.toggle('dark');
        document.querySelectorAll('#themeIcon').forEach(icon => {
            icon.className = isDark ? 'ti ti-moon' : 'ti ti-sun';
        });
        document.querySelectorAll('#themeKnob').forEach(knob => {
            knob.style.transform = isDark ? 'translateX(18px)' : 'translateX(0)';
        });
    });
});

document.getElementById('goToLogin').addEventListener('click', () => showCard('loginCard'));
document.getElementById('goToSignup').addEventListener('click', () => showCard('signupCard'));

let signupEmailValue = '';
let signupScore = 0;

document.getElementById('signupPassword').addEventListener('input', function() {
    signupScore = checkPasswordStrength(this.value, document.getElementById('signupBar1'), document.getElementById('signupBar2'), document.getElementById('signupBar3'));
});

document.getElementById('signupEmail').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('signupSendCodeBtn').click();
});

document.getElementById('signupSendCodeBtn').addEventListener('click', async function() {
    const email = document.getElementById('signupEmail').value.trim();
    const errorEl = document.getElementById('signupEmailError');
    errorEl.textContent = '';

    if (!isValidEmail(email)) {
        errorEl.textContent = 'Enter a valid email address.';
        return;
    }

    setLoading(this, 'Sending...', 'Continue');

    const formData = new FormData();
    formData.append('email', email);

    try {
        const res = await fetch('/signup/send-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            signupEmailValue = email;
            document.getElementById('signupSentTo').textContent = 'Sent to ' + email;
            document.getElementById('signupStep1').style.display = 'none';
            document.getElementById('signupStep2').style.display = 'block';
            startSignupTimer();
            document.querySelector('#signupOtpRow .auth-otp-box').focus();
        } else {
            errorEl.textContent = data.message;
        }
    } catch {
        errorEl.textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

function setupOtpRow(rowId, onComplete) {
    const boxes = document.querySelectorAll('#' + rowId + ' .auth-otp-box');
    boxes.forEach((box, i) => {
        box.addEventListener('input', function() {
            box.classList.remove('wrong', 'correct');
            if (box.value && i < boxes.length - 1) boxes[i + 1].focus();
        });
        box.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && !box.value && i > 0) boxes[i - 1].focus();
            if (e.key === 'Enter') onComplete();
        });
    });
    return boxes;
}

function getOtpValue(boxes) {
    return Array.from(boxes).map(b => b.value).join('');
}

function markOtpResult(boxes, correct) {
    boxes.forEach(b => b.classList.add(correct ? 'correct' : 'wrong'));
    if (!correct) {
        setTimeout(() => boxes.forEach(b => b.classList.remove('wrong')), 400);
    }
}

const signupOtpBoxes = setupOtpRow('signupOtpRow', () => document.getElementById('signupVerifyBtn').click());

let signupResendCountdown = null;

function startSignupTimer() {
    let t = 30;
    document.getElementById('signupResendText').style.display = 'block';
    document.getElementById('signupResendLink').style.display = 'none';
    document.getElementById('signupTimer').textContent = t + 's';

    clearInterval(signupResendCountdown);
    signupResendCountdown = setInterval(() => {
        t--;
        document.getElementById('signupTimer').textContent = t + 's';
        if (t <= 0) {
            clearInterval(signupResendCountdown);
            document.getElementById('signupResendText').style.display = 'none';
            document.getElementById('signupResendLink').style.display = 'block';
        }
    }, 1000);
}

document.getElementById('signupResendLink').addEventListener('click', async function() {
    const formData = new FormData();
    formData.append('email', signupEmailValue);
    await fetch('/signup/send-code', { method: 'POST', body: formData });
    startSignupTimer();
});

document.getElementById('signupVerifyBtn').addEventListener('click', async function() {
    const code = getOtpValue(signupOtpBoxes);
    const errorEl = document.getElementById('signupOtpError');
    errorEl.textContent = '';

    if (code.length !== 6) {
        errorEl.textContent = 'Enter the verification code.';
        return;
    }

    setLoading(this, 'Verifying...', 'Verify');

    const formData = new FormData();
    formData.append('email', signupEmailValue);
    formData.append('code', code);

    try {
        const res = await fetch('/signup/verify-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            markOtpResult(signupOtpBoxes, true);
            setTimeout(() => {
                document.getElementById('signupStep2').style.display = 'none';
                document.getElementById('signupStep3').style.display = 'block';
                document.getElementById('signupName').focus();
            }, 400);
        } else {
            markOtpResult(signupOtpBoxes, false);
            errorEl.textContent = data.blocked ? data.message : 'The verification code is incorrect.';
        }
    } catch {
        errorEl.textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

let newAccountScore = 0;
document.getElementById('signupName').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('signupPassword').focus();
});
document.getElementById('signupPassword').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('signupCreateBtn').click();
});

document.getElementById('signupCreateBtn').addEventListener('click', async function() {
    const name = document.getElementById('signupName').value.trim();
    const password = document.getElementById('signupPassword').value;

    document.getElementById('signupNameError').textContent = '';
    document.getElementById('signupPasswordError').textContent = '';

    let hasError = false;
    if (!name) { document.getElementById('signupNameError').textContent = 'Enter your name.'; hasError = true; }
    if (signupScore < 3) { document.getElementById('signupPasswordError').textContent = 'Choose a stronger password.'; hasError = true; }
    if (hasError) return;

    setLoading(this, 'Creating account...', 'Create account');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', signupEmailValue);
    formData.append('password', password);

    try {
        const res = await fetch('/signup', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showWelcomeScreen();
        } else {
            document.getElementById('signupPasswordError').textContent = data.message;
        }
    } catch {
        document.getElementById('signupPasswordError').textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

function showWelcomeScreen() {
    document.querySelector('.auth-page-wrap').innerHTML = `
        <div class="auth-card" style="text-align:center;">
            <p class="auth-title" style="font-size:22px;">Welcome to JARVIS</p>
            <p class="auth-subtitle">by Aditya</p>
        </div>
    `;
    setTimeout(() => { window.location.href = '/'; }, 1400);
}

document.getElementById('loginEmail').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('loginPassword').focus();
});
document.getElementById('loginPassword').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('loginSubmitBtn').click();
});

document.getElementById('loginSubmitBtn').addEventListener('click', async function() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    document.getElementById('loginEmailError').textContent = '';
    document.getElementById('loginPasswordError').textContent = '';

    let hasError = false;
    if (!email) { document.getElementById('loginEmailError').textContent = 'Enter your email.'; hasError = true; }
    if (!password) { document.getElementById('loginPasswordError').textContent = 'Enter your password.'; hasError = true; }
    if (hasError) return;

    setLoading(this, 'Logging in...', 'Log in');

    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    try {
        const res = await fetch('/login', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            window.location.href = '/';
        } else {
            document.getElementById('loginPasswordError').textContent = data.message;
        }
    } catch {
        document.getElementById('loginPasswordError').textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

document.getElementById('goToForgot').addEventListener('click', () => showCard('forgotEmailCard'));
document.getElementById('backToLoginFromEmail').addEventListener('click', () => showCard('loginCard'));

let forgotEmailValue = '';

document.getElementById('forgotEmail').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('sendCodeBtn').click();
});

document.getElementById('sendCodeBtn').addEventListener('click', async function() {
    const email = document.getElementById('forgotEmail').value.trim();
    const errorEl = document.getElementById('forgotEmailError');
    errorEl.textContent = '';

    if (!isValidEmail(email)) {
        errorEl.textContent = 'Enter a valid email address.';
        return;
    }

    setLoading(this, 'Sending...', 'Send code');

    const formData = new FormData();
    formData.append('email', email);

    try {
        const res = await fetch('/forgot-password/send-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            forgotEmailValue = email;
            document.getElementById('otpSentTo').textContent = 'Sent to ' + email;
            showCard('forgotOtpCard');
            startForgotTimer();
            document.querySelector('#forgotOtpRow .auth-otp-box').focus();
        } else {
            errorEl.textContent = data.message;
        }
    } catch {
        errorEl.textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

const forgotOtpBoxes = setupOtpRow('forgotOtpRow', () => document.getElementById('verifyOtpBtn').click());

let forgotResendCountdown = null;

function startForgotTimer() {
    let t = 30;
    document.getElementById('resendText').style.display = 'block';
    document.getElementById('resendLink').style.display = 'none';
    document.getElementById('resendTimer').textContent = t + 's';

    clearInterval(forgotResendCountdown);
    forgotResendCountdown = setInterval(() => {
        t--;
        document.getElementById('resendTimer').textContent = t + 's';
        if (t <= 0) {
            clearInterval(forgotResendCountdown);
            document.getElementById('resendText').style.display = 'none';
            document.getElementById('resendLink').style.display = 'block';
        }
    }, 1000);
}

document.getElementById('resendLink').addEventListener('click', async function() {
    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    await fetch('/forgot-password/send-code', { method: 'POST', body: formData });
    startForgotTimer();
});

document.getElementById('verifyOtpBtn').addEventListener('click', async function() {
    const code = getOtpValue(forgotOtpBoxes);
    const errorEl = document.getElementById('forgotOtpError');
    errorEl.textContent = '';

    if (code.length !== 6) {
        errorEl.textContent = 'Enter the verification code.';
        return;
    }

    setLoading(this, 'Verifying...', 'Verify');

    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    formData.append('code', code);

    try {
        const res = await fetch('/forgot-password/verify-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            markOtpResult(forgotOtpBoxes, true);
            setTimeout(() => showCard('newPasswordCard'), 400);
        } else {
            markOtpResult(forgotOtpBoxes, false);
            errorEl.textContent = data.blocked ? data.message : (data.message.includes('expired') ? 'This code has expired. Request a new one.' : 'The verification code is incorrect.');
        }
    } catch {
        errorEl.textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});

let newPassScore = 0;
document.getElementById('newPassword').addEventListener('input', function() {
    newPassScore = checkPasswordStrength(this.value, document.getElementById('newBar1'), document.getElementById('newBar2'), document.getElementById('newBar3'));
});

document.getElementById('confirmPassword').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('updatePasswordBtn').click();
});

document.getElementById('updatePasswordBtn').addEventListener('click', async function() {
    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmPassword').value;
    const errorEl = document.getElementById('newPasswordError');
    errorEl.textContent = '';

    if (newPassScore < 3) { errorEl.textContent = 'Choose a stronger password.'; return; }
    if (password !== confirm) { errorEl.textContent = 'Passwords do not match.'; return; }

    setLoading(this, 'Updating...', 'Update password');

    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    formData.append('password', password);

    try {
        const res = await fetch('/forgot-password/reset', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showCard('loginCard');
        } else {
            errorEl.textContent = data.message;
        }
    } catch {
        errorEl.textContent = 'Connection failed. Try again.';
    } finally {
        clearLoading(this);
    }
});