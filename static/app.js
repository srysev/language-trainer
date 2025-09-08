// static/app.js
const $messages = document.getElementById("messages");
const $form = document.getElementById("composer");
const $input = document.getElementById("input");
const $send = document.getElementById("send");
const $typing = document.getElementById("typing");

function uuid() {
    if (crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxx".replace(/x/g, () => ((Math.random() * 36) | 0).toString(36));
}

function getUserSessionId() {
    let id = localStorage.getItem("sprachtrainer_user_session_id");
    if (!id) {
        id = uuid();
        localStorage.setItem("sprachtrainer_user_session_id", id);
    }
    return id;
}

function getSessionId() {
    const userSessionId = getUserSessionId();
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD format
    return `web:${userSessionId}:${today}`;
}

const sessionId = getSessionId();

function scrollToBottom() {
    window.requestAnimationFrame(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    });
}

function bubble(text, who = "bot", { html = false } = {}) {
    const div = document.createElement("div");
    div.className = `bubble ${who}`;
    if (html) {
        // Wir lassen nur <br> zu – alles andere escapen wir rudimentär
        const sanitized = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br>")
            .replace(/&lt;br&gt;/g, "<br>");
        div.innerHTML = sanitized;
    } else {
        div.textContent = text;
    }
    $messages.appendChild(div);
    scrollToBottom();
    return div;
}

function setLoading(loading) {
    $send.disabled = loading || !$input.value.trim();
    $typing.classList.toggle("hidden", !loading);
}

$input.addEventListener("input", () => {
    $send.disabled = !$input.value.trim();
});

$form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = $input.value.trim();
    if (!text) return;

    // Nutzer-Blase
    bubble(text, "user");
    $input.value = "";
    setLoading(true);

    try {
        // Log session usage for web clients
        console.log(`Sending message with session_id: ${sessionId}`);
        
        const params = new URLSearchParams({
            message: text,
            session_id: sessionId,
            stream: "false" // non-streaming
        });

        // Hinweis: Manche Versionen akzeptieren auch /v1/runs – falls /v1/run 404 liefert,
        // nutze '/v1/runs?agent_id=sprachtrainer'.
        const url = `/runs?agent_id=sprachtrainer`;

        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: params
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const textFromApi =
            data?.content ?? data?.message ?? data?.text ?? JSON.stringify(data);

        bubble(textFromApi, "bot", { html: true });
    } catch (err) {
        bubble("Verbindung fehlgeschlagen. Bitte nochmal senden.", "bot");
        console.error(err);
    } finally {
        setLoading(false);
        $input.focus();
    }
});