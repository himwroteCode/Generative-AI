document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("guide-chat-form");
    const input = document.getElementById("guide-user-input");
    const chatBox = document.getElementById("guide-chat-box");
    const typingIndicator = document.getElementById("guide-typing-indicator");
    const layout = document.getElementById("guide-layout");
    const learnToggle = document.getElementById("learn-toggle");

    if (layout && learnToggle) {
        const icon = document.getElementById("learn-toggle-icon");
        function updateIcon() {
            const collapsed = layout.classList.contains("learn-collapsed");
            if (icon) {
                icon.className = collapsed ? "fas fa-chevron-right" : "fas fa-chevron-left";
            }
        }
        const stored = localStorage.getItem("guide-learn-collapsed");
        if (stored === "true") layout.classList.add("learn-collapsed");
        updateIcon();
        learnToggle.addEventListener("click", () => {
            layout.classList.toggle("learn-collapsed");
            localStorage.setItem("guide-learn-collapsed", layout.classList.contains("learn-collapsed"));
            updateIcon();
        });
    }

    function appendMessage(text, isUser) {
        const message = document.createElement("div");
        message.className = "message " + (isUser ? "user-message" : "bot-message");

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        const icon = document.createElement("i");
        icon.className = isUser ? "fas fa-user" : "fas fa-robot";
        avatar.appendChild(icon);

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = text;

        message.appendChild(avatar);
        message.appendChild(bubble);
        chatBox.appendChild(message);
        chatBox.scrollTop = chatBox.scrollHeight;
        return bubble;
    }

    async function typewriter(el, text) {
        el.textContent = "";
        for (let i = 0; i < text.length; i++) {
            el.textContent += text[i];
            chatBox.scrollTop = chatBox.scrollHeight;
            await new Promise(r => setTimeout(r, 12));
        }
    }

    async function sendQuery(query) {
        if (typingIndicator) typingIndicator.classList.remove("hidden");
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const res = await fetch("/ask/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({ message: query }),
            });
            if (typingIndicator) typingIndicator.classList.add("hidden");

            const data = await res.json().catch(() => ({}));
            const bubble = appendMessage("", false);
            if (!res.ok) {
                await typewriter(bubble, data.answer || data.error || "Request failed. Please try again.");
                return;
            }
            await typewriter(bubble, data.answer || "I couldn't process that. Please try again.");
        } catch (err) {
            if (typingIndicator) typingIndicator.classList.add("hidden");
            const bubble = appendMessage("Error sending message. Please try again.", false);
        }
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, true);
        input.value = "";
        sendQuery(text);
    });
});
