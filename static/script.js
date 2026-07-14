const placeholders = [
    "Try: open youtube",
    "Try: what's the time",
    "Try: search cats",
    "Try: who are you",
    "Try: open notepad"
];

let phIndex = 0;
let history = [];
let isListening = false;
let voiceEnabled = false;
let darkMode = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function() {
        isListening = true;
        document.getElementById("micBtn").classList.add("listening");
        document.getElementById("output").innerText = "Listening...";
    };

    recognition.onresult = function(event) {
        let transcript = event.results[0][0].transcript;
        document.getElementById("commandBox").value = transcript;
        sendCommand();
    };

    recognition.onerror = function() {
        document.getElementById("output").innerText = "I could not hear you clearly.";
    };

    recognition.onend = function() {
        isListening = false;
        document.getElementById("micBtn").classList.remove("listening");
    };
}

setInterval(() => {
    phIndex = (phIndex + 1) % placeholders.length;
    document.getElementById("commandBox").placeholder = placeholders[phIndex];
}, 3000);

function updateClock() {
    let now = new Date();
    document.getElementById("clock").innerText = now.toLocaleTimeString();
}

function speak(text) {
    if (!voiceEnabled) return;
    if (!("speechSynthesis" in window)) return;

    let speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-IN";
    speech.rate = 1;
    speech.pitch = 1;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
}

function toggleVoice() {
    voiceEnabled = !voiceEnabled;

    let toggle = document.getElementById("voiceToggle");

    if (voiceEnabled) {
        toggle.innerText = "ON";
        toggle.classList.add("on");
    } else {
        toggle.innerText = "OFF";
        toggle.classList.remove("on");
        window.speechSynthesis.cancel();
    }
}

function toggleTheme() {
    darkMode = !darkMode;

    let toggle = document.getElementById("themeToggle");

    if (darkMode) {
        document.body.classList.add("dark");
        toggle.innerText = "DARK";
        toggle.classList.add("on");
    } else {
        document.body.classList.remove("dark");
        toggle.innerText = "LIGHT";
        toggle.classList.remove("on");
    }
}

function startListening() {
    if (!recognition) {
        document.getElementById("output").innerText = "Voice input is not supported in this browser.";
        return;
    }

    if (isListening) {
        recognition.stop();
        return;
    }

    recognition.start();
}

function filterNotes() {

    let searchValue =
        document.getElementById(
            "notesSearch"
        ).value.toLowerCase();

    let notes =
        document.querySelectorAll(
            ".note-item"
        );

    notes.forEach(note => {

        let text =
            note.innerText.toLowerCase();

        if (
            text.includes(searchValue)
        ) {

            note.style.display = "block";

        } else {

            note.style.display = "none";

        }

    });
}

let pendingDeleteId = null;

function confirmDelete(noteId) {
    pendingDeleteId = noteId;
    let modal = document.getElementById("deleteModal");
    modal.style.display = "flex";
}

document.getElementById("deleteCancelBtn").addEventListener("click", () => {
    pendingDeleteId = null;
    document.getElementById("deleteModal").style.display = "none";
});

document.getElementById("deleteConfirmBtn").addEventListener("click", () => {
    if (pendingDeleteId !== null) {
        deleteNote(pendingDeleteId);
        pendingDeleteId = null;
        document.getElementById("deleteModal").style.display = "none";
    }
});

document.getElementById("deleteModal").addEventListener("click", (e) => {
    if (e.target === document.getElementById("deleteModal")) {
        pendingDeleteId = null;
        document.getElementById("deleteModal").style.display = "none";
    }
});

async function deleteNote(noteId) {

    try {

        let response = await fetch(
            `/notes/delete/${noteId}`,
            {
                method: "DELETE"
            }
        );

        let data = await response.json();

        if (data.success) {

            loadNotes();

        }

    }

    catch {

        alert("Failed to delete note.");

    }
}

async function loadNotes() {

    try {

        let username = localStorage.getItem("jarvisUserName") || "";
        let response = await fetch("/notes?username=" + encodeURIComponent(username));

        let data = await response.json();

        let notesContent =
            document.getElementById("notesContent");

        if (
            !data.success ||
            data.notes.length === 0
        ) {

            notesContent.innerHTML =
                "<p>No notes found.</p>";

            document.getElementById(
                "notesTitle"
                    ).innerText =
            "Notes (0)";

            return;
        }

        let html = "";

        data.notes.forEach((note, index) => {

        html += `
<div class="note-item">

    <div class="note-row">

        <span>
            ${index + 1}. ${note.text}
        </span>

        <button
            class="delete-note-btn"
            onclick="confirmDelete(${note.id})"
        >
            Delete
        </button>

    </div>

    <div class="note-timestamp">
        <span class="note-date">
            <i class="ti ti-calendar"></i>
            ${note.created_at ? note.created_at.split(" ").slice(0, 3).join(" ") : "No date"}
        </span>
        <span class="note-time">
            <i class="ti ti-clock"></i>
            ${note.created_at ? note.created_at.split(" ")[3] : ""}
        </span>
    </div>

</div>
`;

        });

        document.getElementById(
            "notesTitle"
                ).innerText =
        `Notes (${data.notes.length})`;

        notesContent.innerHTML = html;

    }

    catch {

        document.getElementById(
            "notesContent"
        ).innerHTML =
        "<p>Failed to load notes.</p>";
    }
}

async function sendCommand() {
    let inputBox = document.getElementById("commandBox");
    let command = inputBox.value.trim();

    if (!command) return;

        if (["show notes", "show note", "notes", "open notes"].includes(command.toLowerCase())) {
        notesOverlay.style.display = "flex";
        loadNotes();

        document.getElementById("output").innerText = "Opening notes.";
        document.getElementById("outputCard").classList.remove("error");
        document.getElementById("outputCard").classList.add("success");

        history.unshift(command);
        if (history.length > 3) history.pop();
        updateHistory();

        inputBox.value = "";
        inputBox.focus();

        return;
    }

    let btn = document.getElementById("execBtn");
    let outputCard = document.getElementById("outputCard");
    let output = document.getElementById("output");

    btn.innerText = "Thinking...";
    btn.disabled = true;
    output.innerText = "Processing command...";

    let formData = new FormData();
    formData.append("command", command);
    formData.append("username", localStorage.getItem("jarvisUserName") || "");

    try {
        let response = await fetch("/command", {
            method: "POST",
            body: formData
        });

        let data = await response.json();

        output.innerText = data.response;
        speak(data.response);

        outputCard.classList.remove("success", "error");

        if (data.success) {
            outputCard.classList.add("success");
        } else {
            outputCard.classList.add("error");
        }

        history.unshift(command);
        if (history.length > 3) history.pop();
        updateHistory();

        inputBox.value = "";

    } catch (error) {
        let errorMessage = "JARVIS connection failed. Please check if Flask is running.";
        output.innerText = errorMessage;
        speak(errorMessage);

        outputCard.classList.remove("success");
        outputCard.classList.add("error");

    } finally {
        btn.innerText = "Ask JARVIS";
        btn.disabled = false;
        inputBox.focus();
    }
}

function updateHistory() {
    let list = document.getElementById("historyList");
    let card = document.getElementById("historyCard");

    if (history.length === 0) {
        card.style.display = "none";
        return;
    }

    card.style.display = "block";
    list.innerHTML = "";

    history.forEach(cmd => {
        let li = document.createElement("li");
        li.innerText = cmd;
        list.appendChild(li);
    });
}

document.getElementById("commandBox").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendCommand();
    }
});

document
.getElementById("notesSearch")
.addEventListener(
    "input",
    filterNotes
);

setInterval(updateClock, 1000);
updateClock();

const notesBtn = document.getElementById("notesBtn");

const notesOverlay = document.getElementById("notesOverlay");

const closeNotesBtn = document.getElementById("closeNotesBtn");

let addNoteListening = false;
let addNoteRecognition = null;

if (SpeechRecognition) {
    addNoteRecognition = new SpeechRecognition();
    addNoteRecognition.lang = "en-IN";
    addNoteRecognition.continuous = false;
    addNoteRecognition.interimResults = false;

    addNoteRecognition.onstart = function() {
        addNoteListening = true;

        let micBtn = document.getElementById("addNoteMicBtn");
        let noteBox = document.getElementById("addNoteText");

        micBtn.classList.add("listening");
        noteBox.placeholder = "Listening...";
    };

    addNoteRecognition.onresult = function(event) {
        let transcript = event.results[0][0].transcript.trim();
        let noteBox = document.getElementById("addNoteText");

        if (noteBox.value.trim()) {
            noteBox.value += " " + transcript;
        } else {
            noteBox.value = transcript;
        }

        noteBox.focus();
    };

    addNoteRecognition.onerror = function(event) {
        let noteBox = document.getElementById("addNoteText");

        noteBox.placeholder = "Voice input failed. Try again.";
        console.log("ADD NOTE MIC ERROR:", event.error);
    };

    addNoteRecognition.onend = function() {
        addNoteListening = false;

        let micBtn = document.getElementById("addNoteMicBtn");
        let noteBox = document.getElementById("addNoteText");

        micBtn.classList.remove("listening");
        noteBox.placeholder = "Type your note here...";
    };
}

function openAddNoteModal() {
    document.getElementById("addNoteModal").style.display = "flex";
    document.getElementById("addNoteText").value = "";
    document.getElementById("addNoteText").focus();
}

function closeAddNoteModal() {
    document.getElementById("addNoteModal").style.display = "none";
    if (addNoteListening && addNoteRecognition) {
        addNoteRecognition.stop();
    }
}

async function saveNewNote() {
    let text = document.getElementById("addNoteText").value.trim();

    if (!text) {
        document.getElementById("addNoteText").focus();
        return;
    }

    let saveBtn = document.getElementById("addNoteSaveBtn");
    saveBtn.innerText = "Saving...";
    saveBtn.disabled = true;

    let formData = new FormData();
    formData.append("command", "note " + text);
    formData.append("username", localStorage.getItem("jarvisUserName") || "");

    try {
        let response = await fetch("/command", {
            method: "POST",
            body: formData
        });

        let data = await response.json();

        if (data.success) {
            closeAddNoteModal();
            loadNotes();
        }

    } catch {
        saveBtn.innerText = "Save Note";
        saveBtn.disabled = false;
    }

    saveBtn.innerText = "Save Note";
    saveBtn.disabled = false;
}

document.getElementById("addNoteCloseBtn").addEventListener("click", closeAddNoteModal);
document.getElementById("addNoteCancelBtn").addEventListener("click", closeAddNoteModal);

document.getElementById("addNoteSaveBtn").addEventListener("click", saveNewNote);

document.getElementById("addNoteText").addEventListener("keydown", function(e) {
    if (e.key === "Enter" && e.ctrlKey) {
        saveNewNote();
    }
});

document.getElementById("addNoteMicBtn").addEventListener("click", function() {
    if (!addNoteRecognition) {
        document.getElementById("addNoteText").placeholder =
            "Voice input is not supported in this browser.";
        return;
    }

    if (isListening && recognition) {
        recognition.stop();
    }

    if (addNoteListening) {
        addNoteRecognition.stop();
    } else {
        addNoteRecognition.start();
    }
});

document.getElementById("addNoteModal").addEventListener("click", function(e) {
    if (e.target === document.getElementById("addNoteModal")) {
        closeAddNoteModal();
    }
});

notesBtn.addEventListener("click", () => {

    notesOverlay.style.display = "flex";

    loadNotes();
});

closeNotesBtn.addEventListener("click", () => {

    notesOverlay.style.display = "none";

});

const profilePill = document.getElementById("profilePill");
const profileName = document.getElementById("profileName");
const logoutBtn = document.getElementById("logoutOpt");
const dropdownMenu = document.getElementById("dropdownMenu");

profilePill.addEventListener("click", function(e) {
    e.stopPropagation();
    dropdownMenu.style.display = dropdownMenu.style.display === "block" ? "none" : "block";
});

document.addEventListener("click", function() {
    dropdownMenu.style.display = "none";
});

logoutBtn.addEventListener("click", function() {
    dropdownMenu.style.display = "none";
    document.getElementById("logoutConfirmModal").style.display = "flex";
});

document.getElementById("logoutCancelBtn").addEventListener("click", function() {
    document.getElementById("logoutConfirmModal").style.display = "none";
});

document.getElementById("logoutConfirmBtn").addEventListener("click", async function() {
    await fetch("/logout", { method: "POST" });
    window.location.href = "/";
});

const editNameOverlay = document.getElementById("editNameOverlay");
const editNameInput = document.getElementById("editNameInput");

document.getElementById("editNameOpt").addEventListener("click", function () {
    editNameInput.value = profileName.textContent;
    editNameOverlay.style.display = "flex";
    editNameInput.focus();
    dropdownMenu.style.display = "none";
});

document.getElementById("editNameCancelBtn").addEventListener("click", function () {
    editNameOverlay.style.display = "none";
});

document.getElementById("editNameSaveBtn").addEventListener("click", saveEditedName);

editNameInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        saveEditedName();
    }
});

function saveEditedName() {

    const newName = editNameInput.value.trim();

    if (!newName) {
        showToast("Please enter your name.", "error");
        return;
    }

    const firstName = newName.split(" ")[0];

    const saveBtn = document.getElementById("editNameSaveBtn");

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    fetch("/update-name", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: "name=" + encodeURIComponent(firstName)
    })
    .then(res => res.json())
    .then(data => {

        saveBtn.disabled = false;
        saveBtn.textContent = "Save";

        if (data.success) {

            profileName.textContent = data.name || firstName;

            editNameOverlay.style.display = "none";

            console.log("Toast reached");

            showToast("Name updated successfully.");

        } else {

            showToast(data.message || "Couldn't update your name.", "error");

        }

    })
    .catch(() => {

        saveBtn.disabled = false;
        saveBtn.textContent = "Save";

        showToast("Something went wrong.", "error");

    });

}

fetch("/notes?dummy=1").then(() => {});
profileName.textContent = window.CURRENT_USER_NAME || "User";

function showToast(message,type="success"){

    const toast=document.getElementById("toast");

    document.getElementById("toastTitle").textContent=
        type==="error" ? "Error" : "Success";

    document.getElementById("toastMessage").textContent=message;

    toast.classList.remove("error");

    if(type==="error"){
        toast.classList.add("error");
    }

    toast.classList.add("show");

    clearTimeout(window.toastTimer);

    window.toastTimer=setTimeout(()=>{
        toast.classList.remove("show");
    },2200);

}

// About Modal
const aboutOverlay = document.getElementById("aboutOverlay");
const aboutCloseBtn = document.getElementById("aboutCloseBtn");
const aboutOpt = document.getElementById("aboutOpt");

if (aboutOpt) {
    aboutOpt.addEventListener("click", function(e) {
        e.stopPropagation();
        dropdownMenu.style.display = "none";
        aboutOverlay.style.display = "flex";
    });
}

if (aboutCloseBtn) {
    aboutCloseBtn.addEventListener("click", function() {
        aboutOverlay.style.display = "none";
    });
}

if (aboutOverlay) {
    aboutOverlay.addEventListener("click", function(e) {
        if (e.target === aboutOverlay) {
            aboutOverlay.style.display = "none";
        }
    });
}