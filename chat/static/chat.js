let currentConversationId = null;

const chatMessagesEl = document.getElementById('chatMessages');
const chatConvListEl = document.getElementById('chatConvList');
const chatInputEl = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const chatNewBtn = document.getElementById('chatNewBtn');
const chatSidebarEl = document.getElementById('chatSidebar');
const chatSidebarToggle = document.getElementById('chatSidebarToggle');

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function loadConversations() {
    try {
        const res = await fetch('/chat/list');
        const data = await res.json();

        if (!data.success) return;

        chatConvListEl.innerHTML = '';

        if (data.conversations.length === 0) {
            chatConvListEl.innerHTML = '<div class="chat-empty-sidebar">No chats yet</div>';
            return;
        }

        data.conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'chat-conv-item' + (conv.id === currentConversationId ? ' active' : '');
            item.dataset.id = conv.id;

            item.innerHTML = `
                <span class="chat-conv-title">${escapeHtml(conv.title)}</span>
                <div class="chat-conv-actions">
                    <i class="ti ti-edit" data-action="rename"></i>
                    <i class="ti ti-trash" data-action="delete"></i>
                </div>
            `;

            item.querySelector('.chat-conv-title').addEventListener('click', () => selectConversation(conv.id));

            item.querySelector('[data-action="rename"]').addEventListener('click', (e) => {
                e.stopPropagation();
                startRename(item, conv.id, conv.title);
            });

            item.querySelector('[data-action="delete"]').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteConversation(conv.id);
            });

            chatConvListEl.appendChild(item);
        });
    } catch (err) {
        console.error('LOAD CONVERSATIONS ERROR:', err);
    }
}

function startRename(item, id, oldTitle) {
    const titleEl = item.querySelector('.chat-conv-title');
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldTitle;
    input.className = 'chat-conv-title-input';

    titleEl.replaceWith(input);
    input.focus();
    input.select();

    async function commit() {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== oldTitle) {
            await renameConversation(id, newTitle);
        } else {
            await loadConversations();
        }
    }

    input.addEventListener('blur', commit);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') input.blur();
    });
}

async function renameConversation(id, title) {
    try {
        const formData = new FormData();
        formData.append('title', title);
        await fetch(`/chat/${id}/rename`, { method: 'POST', body: formData });
        await loadConversations();
    } catch (err) {
        console.error('RENAME ERROR:', err);
    }
}

async function deleteConversation(id) {
    try {
        await fetch(`/chat/${id}/delete`, { method: 'DELETE' });

        if (id === currentConversationId) {
            currentConversationId = null;
            chatMessagesEl.innerHTML = '<div class="chat-empty-state">Start a new chat</div>';
        }

        await loadConversations();
    } catch (err) {
        console.error('DELETE ERROR:', err);
    }
}

async function selectConversation(id) {
    currentConversationId = id;
    closeSidebarOnMobile();

    document.querySelectorAll('.chat-conv-item').forEach(el => {
        el.classList.toggle('active', Number(el.dataset.id) === id);
    });

    try {
        const res = await fetch(`/chat/${id}/messages`);
        const data = await res.json();

        chatMessagesEl.innerHTML = '';

        if (!data.success || data.messages.length === 0) {
            chatMessagesEl.innerHTML = '<div class="chat-empty-state">No messages yet</div>';
            return;
        }

        data.messages.forEach(msg => appendBubble(msg.role, msg.content, msg.created_at));
        scrollToBottom();
    } catch (err) {
        console.error('LOAD MESSAGES ERROR:', err);
    }
}

function renderMarkdownBold(escapedText) {
    return escapedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function appendBubble(role, content, time) {
    if (chatMessagesEl.querySelector('.chat-empty-state')) {
        chatMessagesEl.innerHTML = '';
    }

    const row = document.createElement('div');
    row.className = 'chat-bubble-row ' + (role === 'user' ? 'user' : 'jarvis');

    const safeContent = role === 'user'
        ? escapeHtml(content)
        : renderMarkdownBold(escapeHtml(content));

    row.innerHTML = `
        <div class="chat-bubble">${safeContent}</div>
        <div class="chat-bubble-time">${time || ''}</div>
    `;

    chatMessagesEl.appendChild(row);
}

function showTyping() {
    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.id = 'chatTypingIndicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    chatMessagesEl.appendChild(typing);
    scrollToBottom();
}

function hideTyping() {
    const typing = document.getElementById('chatTypingIndicator');
    if (typing) typing.remove();
}

function scrollToBottom() {
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

async function ensureConversation() {
    if (currentConversationId) return currentConversationId;

    try {
        const res = await fetch('/chat/new', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            currentConversationId = data.conversation_id;
            await loadConversations();
            return currentConversationId;
        }
    } catch (err) {
        console.error('NEW CONVERSATION ERROR:', err);
    }

    return null;
}

async function sendChatMessage() {
    const message = chatInputEl.value.trim();
    if (!message) return;

    const convId = await ensureConversation();
    if (!convId) return;

    chatInputEl.value = '';
    appendBubble('user', message, '');
    scrollToBottom();
    showTyping();

    try {
        const formData = new FormData();
        formData.append('message', message);

        const res = await fetch(`/chat/${convId}/send`, { method: 'POST', body: formData });
        const data = await res.json();

        hideTyping();

        if (data.success) {
            appendBubble('jarvis', data.response, '');
            scrollToBottom();
            await loadConversations();
        } else {
            appendBubble('jarvis', data.message || 'Something went wrong.', '');
        }
    } catch (err) {
        hideTyping();
        appendBubble('jarvis', 'Connection failed. Try again.', '');
        console.error('SEND MESSAGE ERROR:', err);
    }
}

function closeSidebarOnMobile() {
    if (chatSidebarEl) chatSidebarEl.classList.remove('open');
}

if (chatSendBtn) {
    chatSendBtn.addEventListener('click', sendChatMessage);
}

if (chatInputEl) {
    chatInputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

if (chatNewBtn) {
    chatNewBtn.addEventListener('click', async () => {
        currentConversationId = null;
        chatMessagesEl.innerHTML = '<div class="chat-empty-state">Start a new chat</div>';
        chatInputEl.focus();
        document.querySelectorAll('.chat-conv-item').forEach(el => el.classList.remove('active'));
        closeSidebarOnMobile();
    });
}

if (chatSidebarToggle) {
    chatSidebarToggle.addEventListener('click', () => {
        chatSidebarEl.classList.toggle('open');
    });
}

document.addEventListener('DOMContentLoaded', loadConversations);

const chatMicBtn = document.getElementById('chatMicBtn');
if (chatMicBtn) {
    chatMicBtn.addEventListener('click', () => {
        if (typeof showToast === 'function') {
            showToast('Voice input coming soon', 'error');
        }
    });
}