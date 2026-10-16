/* ═══════════════════════════════════════════════════════════════════════════
   Smart Money Terminal — Embedded AI Chat
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
    createChatWidget();
});

function createChatWidget() {
    const html = `
    <!-- Chat Widget Toggle -->
    <div id="aiChatToggle" style="position:fixed; bottom:24px; right:24px; width:50px; height:50px; background:linear-gradient(135deg, #8B5CF6, #6D28D9); border-radius:50%; box-shadow:0 4px 20px rgba(124,58,237,0.4); display:flex; align-items:center; justify-content:center; cursor:pointer; z-index:9998; transition:transform 0.2s;">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
    </div>

    <!-- Chat Window -->
    <div id="aiChatWindow" style="position:fixed; bottom:85px; right:24px; width:360px; height:500px; max-height:calc(100vh - 100px); background:var(--surface-1, #0f121b); border:1px solid rgba(124,58,237,0.3); border-radius:12px; box-shadow:0 8px 32px rgba(0,0,0,0.5); display:none; flex-direction:column; z-index:9999; overflow:hidden;">
      
      <!-- Header -->
      <div style="padding:12px 16px; background:linear-gradient(135deg, rgba(124,58,237,0.2) 0%, transparent 100%); border-bottom:1px solid rgba(124,58,237,0.2); display:flex; justify-content:space-between; align-items:center;">
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="width:8px; height:8px; background:#10B981; border-radius:50%; box-shadow:0 0 8px #10B981;"></div>
          <strong style="color:#E9D5FF; font-size:14px;">SmartMoney AI</strong>
        </div>
        <button id="aiChatCloseBtn" style="background:transparent; border:none; color:var(--text-muted, #9ca3af); cursor:pointer; padding:4px;">✕</button>
      </div>

      <!-- Messages Area -->
      <div id="aiChatMessages" style="flex:1; padding:16px; overflow-y:auto; display:flex; flex-direction:column; gap:12px; font-size:13px; line-height:1.5;">
        <div style="background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.2); padding:10px 14px; border-radius:8px 8px 8px 0; color:var(--text, #e2e8f0); max-width:85%; align-self:flex-start;">
          Hello! I have access to your watchlist and live market data. How can I help you analyze the market today?
        </div>
      </div>

      <!-- Input Area -->
      <div style="padding:12px; border-top:1px solid var(--border, #1e293b); background:var(--surface-2, #161a25); display:flex; gap:8px;">
        <input type="text" id="aiChatInput" placeholder="Ask about stocks, sectors, or trends..." style="flex:1; background:var(--surface-1, #0f121b); border:1px solid var(--border, #1e293b); color:var(--text, #e2e8f0); padding:8px 12px; border-radius:20px; outline:none; font-size:13px;">
        <button id="aiChatSendBtn" style="background:#8B5CF6; border:none; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; cursor:pointer;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </div>
  `;

    document.body.insertAdjacentHTML("beforeend", html);

    const toggle = document.getElementById("aiChatToggle");
    const win = document.getElementById("aiChatWindow");
    const close = document.getElementById("aiChatCloseBtn");
    const input = document.getElementById("aiChatInput");
    const send = document.getElementById("aiChatSendBtn");
    const msgs = document.getElementById("aiChatMessages");

    let isSending = false;

    toggle.addEventListener("click", () => {
        win.style.display = win.style.display === "none" ? "flex" : "none";
        if (win.style.display === "flex") input.focus();
    });

    close.addEventListener("click", () => {
        win.style.display = "none";
    });

    async function sendMessage() {
        const text = input.value.trim();
        if (!text || isSending) return;

        // Add user message
        msgs.insertAdjacentHTML("beforeend", `
      <div style="background:var(--surface-3, #1e293b); padding:10px 14px; border-radius:8px 8px 0 8px; color:var(--text, #e2e8f0); max-width:85%; align-self:flex-end;">
        ${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}
      </div>
    `);

        input.value = "";
        isSending = true;

        // Add loading indicator
        const loaderId = "loader-" + Date.now();
        msgs.insertAdjacentHTML("beforeend", `
      <div id="${loaderId}" style="align-self:flex-start; display:flex; gap:4px; padding:10px 14px;">
        <div style="width:6px; height:6px; background:#8B5CF6; border-radius:50%; animation:bounce 1.4s infinite ease-in-out both;"></div>
        <div style="width:6px; height:6px; background:#8B5CF6; border-radius:50%; animation:bounce 1.4s infinite ease-in-out both; animation-delay:0.16s;"></div>
        <div style="width:6px; height:6px; background:#8B5CF6; border-radius:50%; animation:bounce 1.4s infinite ease-in-out both; animation-delay:0.32s;"></div>
        <style>@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }</style>
      </div>
    `);
        msgs.scrollTo(0, msgs.scrollHeight);

        try {
            const res = await fetch("/api/ai/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            document.getElementById(loaderId).remove();

            if (!res.ok) throw new Error(data.error || "Failed to communicate");

            msgs.insertAdjacentHTML("beforeend", `
        <div style="background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.2); padding:10px 14px; border-radius:8px 8px 8px 0; color:var(--text, #e2e8f0); max-width:85%; align-self:flex-start;">
          ${data.response.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>")}
        </div>
      `);

        } catch (e) {
            document.getElementById(loaderId)?.remove();
            msgs.insertAdjacentHTML("beforeend", `
        <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); color:#FCA5A5; padding:8px 12px; border-radius:8px; align-self:center; font-size:12px;">
          ${e.message}
        </div>
      `);
        } finally {
            isSending = false;
            msgs.scrollTo(0, msgs.scrollHeight);
            input.focus();
        }
    }

    send.addEventListener("click", sendMessage);
    input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}
