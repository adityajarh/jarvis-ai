function showCard(id) {
    document.querySelectorAll('.auth-card').forEach(c => c.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}

function showToast(success, message) {
    const toast = document.getElementById('authToast');
    const icon = document.getElementById('authToastIcon');
    const text = document.getElementById('authToastText');
    icon.className = success ? 'ti ti-circle-check' : 'ti ti-alert-circle';
    text.textContent = message;
    toast.className = 'feedback-toast ' + (success ? 'success' : 'error');
    setTimeout(() => { toast.className = 'feedback-toast'; }, 3000);
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
    });
});

document.getElementById('goToLogin').addEventListener('click', () => showCard('loginCard'));
document.getElementById('goToSignup').addEventListener('click', () => showCard('signupCard'));

let signupScore = 0;
document.getElementById('signupPassword').addEventListener('input', function() {
    signupScore = checkPasswordStrength(this.value, document.getElementById('signupBar1'), document.getElementById('signupBar2'), document.getElementById('signupBar3'));
});

document.getElementById('signupSubmitBtn').addEventListener('click', async function() {
    const name = document.getElementById('signupName').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value;

    document.getElementById('signupNameError').textContent = '';
    document.getElementById('signupEmailError').textContent = '';
    document.getElementById('signupPasswordError').textContent = '';

    let hasError = false;
    if (!name) { document.getElementById('signupNameError').textContent = 'Enter your name'; hasError = true; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { document.getElementById('signupEmailError').textContent = 'Enter a valid email'; hasError = true; }
    if (signupScore < 3) { document.getElementById('signupPasswordError').textContent = 'Password must be Strong'; hasError = true; }

    if (hasError) return;

    this.textContent = 'Creating account...';
    this.disabled = true;

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('password', password);

    try {
        const res = await fetch('/signup', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showToast(true, 'Account created!');
            setTimeout(() => { window.location.href = '/'; }, 800);
        } else {
            document.getElementById('signupEmailError').textContent = data.message;
        }
    } catch {
        showToast(false, 'Connection failed.');
    } finally {
        this.textContent = 'Sign Up';
        this.disabled = false;
    }
});

document.getElementById('loginSubmitBtn').addEventListener('click', async function() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    document.getElementById('loginEmailError').textContent = '';
    document.getElementById('loginPasswordError').textContent = '';

    let hasError = false;
    if (!email) { document.getElementById('loginEmailError').textContent = 'Enter your email'; hasError = true; }
    if (!password) { document.getElementById('loginPasswordError').textContent = 'Enter your password'; hasError = true; }

    if (hasError) return;

    this.textContent = 'Logging in...';
    this.disabled = true;

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
        showToast(false, 'Connection failed.');
    } finally {
        this.textContent = 'Log In';
        this.disabled = false;
    }
});

let forgotEmailValue = '';
let resendCountdown = null;

document.getElementById('goToForgot').addEventListener('click', () => showCard('forgotEmailCard'));
document.getElementById('backToLoginFromEmail').addEventListener('click', () => showCard('loginCard'));

document.getElementById('sendCodeBtn').addEventListener('click', async function() {
    const email = document.getElementById('forgotEmail').value.trim();
    document.getElementById('forgotEmailError').textContent = '';

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        document.getElementById('forgotEmailError').textContent = 'Enter a valid email';
        return;
    }

    this.textContent = 'Sending...';
    this.disabled = true;

    const formData = new FormData();
    formData.append('email', email);

    try {
        const res = await fetch('/forgot-password/send-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            forgotEmailValue = email;
            document.getElementById('otpSentTo').textContent = 'Sent to ' + email;
            showCard('forgotOtpCard');
            startResendTimer();
        } else {
            document.getElementById('forgotEmailError').textContent = data.message;
        }
    } catch {
        showToast(false, 'Connection failed.');
    } finally {
        this.textContent = 'Send Code';
        this.disabled = false;
    }
});

function startResendTimer() {
    let timeLeft = 30;
    document.getElementById('resendText').style.display = 'block';
    document.getElementById('resendLink').style.display = 'none';
    document.getElementById('resendTimer').textContent = timeLeft;

    clearInterval(resendCountdown);
    resendCountdown = setInterval(() => {
        timeLeft--;
        document.getElementById('resendTimer').textContent = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(resendCountdown);
            document.getElementById('resendText').style.display = 'none';
            document.getElementById('resendLink').style.display = 'block';
        }
    }, 1000);
}

document.getElementById('resendLink').addEventListener('click', async function() {
    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    await fetch('/forgot-password/send-code', { method: 'POST', body: formData });
    showToast(true, 'New code sent');
    startResendTimer();
});

const otpBoxes = document.querySelectorAll('.auth-otp-box');
otpBoxes.forEach((box, i) => {
    box.addEventListener('input', function() {
        if (box.value && i < otpBoxes.length - 1) otpBoxes[i + 1].focus();
    });
});

document.getElementById('verifyOtpBtn').addEventListener('click', async function() {
    const code = Array.from(otpBoxes).map(b => b.value).join('');
    document.getElementById('otpError').textContent = '';

    if (code.length !== 6) {
        document.getElementById('otpError').textContent = 'Enter all 6 digits';
        return;
    }

    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    formData.append('code', code);

    try {
        const res = await fetch('/forgot-password/verify-code', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showCard('newPasswordCard');
        } else if (data.blocked) {
            showToast(false, data.message);
        } else {
            document.getElementById('otpError').textContent = data.message;
            otpBoxes.forEach(b => b.style.borderColor = 'var(--danger)');
        }
    } catch {
        showToast(false, 'Connection failed.');
    }
});

let newPassScore = 0;
document.getElementById('newPassword').addEventListener('input', function() {
    newPassScore = checkPasswordStrength(this.value, document.getElementById('newBar1'), document.getElementById('newBar2'), document.getElementById('newBar3'));
});

document.getElementById('updatePasswordBtn').addEventListener('click', async function() {
    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmPassword').value;
    document.getElementById('newPasswordError').textContent = '';

    if (newPassScore < 3) {
        document.getElementById('newPasswordError').textContent = 'Password must be Strong';
        return;
    }
    if (password !== confirm) {
        document.getElementById('newPasswordError').textContent = 'Passwords do not match';
        return;
    }

    this.textContent = 'Updating...';
    this.disabled = true;

    const formData = new FormData();
    formData.append('email', forgotEmailValue);
    formData.append('password', password);

    try {
        const res = await fetch('/forgot-password/reset', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showToast(true, 'Password updated!');
            setTimeout(() => { showCard('loginCard'); }, 1000);
        } else {
            document.getElementById('newPasswordError').textContent = data.message;
        }
    } catch {
        showToast(false, 'Connection failed.');
    } finally {
        this.textContent = 'Update Password';
        this.disabled = false;
    }
});