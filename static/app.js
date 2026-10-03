let chatHistory = [];
let pendingActionData = null;

// Initialize app
document.addEventListener("DOMContentLoaded", () => {
  fetchSystemStatus();
  fetchModels();
  setInterval(fetchSystemStatus, 8000); // refresh metrics every 8s

  const textarea = document.getElementById("prompt-input");
  textarea.addEventListener("input", autoResizeTextarea);
});

function autoResizeTextarea() {
  const textarea = document.getElementById("prompt-input");
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("chat-form").dispatchEvent(new Event("submit"));
  }
}

async function fetchSystemStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();
    
    if (data.system && !data.system.error) {
      document.getElementById("cpu-stat").innerText = `${data.system.cpu_percent}%`;
      document.getElementById("ram-stat").innerText = `${data.system.ram_used_gb}/${data.system.ram_total_gb} GB`;
      document.getElementById("disk-stat").innerText = `${data.system.disk_free_gb} GB`;
    }
  } catch (err) {
    console.error("Status fetch error:", err);
  }
}

async function fetchModels() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) return;
    const data = await res.json();
    const select = document.getElementById("model-selector");
    if (data.models && data.models.length > 0) {
      select.innerHTML = "";
      data.models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.innerText = m;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Models fetch error:", err);
  }
}

function setInputAndSend(text) {
  const input = document.getElementById("prompt-input");
  input.value = text;
  autoResizeTextarea();
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));
}

function promptScrapeUrl() {
  const url = prompt("Enter the webpage URL to scrape and summarize:", "https://news.ycombinator.com");
  if (url) {
    runQuickAction("scrape_url", url);
  }
}

async function runQuickAction(actionType, param = null) {
  const model = document.getElementById("model-selector").value;
  const actionLabels = {
    system_health: "Running System Health Check...",
    organize_downloads: "Previewing Downloads Folder Organization...",
    clean_temp_preview: "Auditing Temp Directory Space...",
    scrape_url: `Scraping & Summarizing: ${param}...`,
    list_workspace: "Inspecting Workspace Structure..."
  };

  const label = actionLabels[actionType] || "Running Quick Action...";
  appendMessage("user", label);
  showThinking();

  try {
    const res = await fetch("/api/quick-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_type: actionType,
        target_param: param,
        model: model
      })
    });

    hideThinking();
    const data = await res.json();
    handleAgentResponse(data);
  } catch (err) {
    hideThinking();
    appendMessage("agent", `Error executing quick action: ${err.message}`);
  }
}

async function handleSend(e) {
  e.preventDefault();
  const input = document.getElementById("prompt-input");
  const prompt = input.value.trim();
  if (!prompt) return;

  const model = document.getElementById("model-selector").value;
  appendMessage("user", prompt);
  input.value = "";
  autoResizeTextarea();
  showThinking();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt,
        model: model,
        history: chatHistory
      })
    });

    hideThinking();
    const data = await res.json();
    
    // Track conversation history
    chatHistory.push({ role: "user", content: prompt });
    if (data.response) {
      chatHistory.push({ role: "assistant", content: data.response });
    }

    handleAgentResponse(data);
  } catch (err) {
    hideThinking();
    appendMessage("agent", `Connection error: ${err.message}`);
  }
}

function handleAgentResponse(data) {
  if (data.requires_confirmation && data.pending_action) {
    pendingActionData = data.pending_action;
    showConfirmModal(data.pending_action);
  }
  
  appendMessage("agent", data.response || "Task completed.", data.steps || []);
}

function appendMessage(sender, text, steps = []) {
  const container = document.getElementById("chat-messages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}-message`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.innerText = sender === "user" ? "👤" : "⚡";

  const body = document.createElement("div");
  body.className = "msg-body";

  // If there are tool steps, render them first
  if (steps && steps.length > 0) {
    steps.forEach(step => {
      const stepDiv = document.createElement("div");
      stepDiv.className = "tool-step";
      
      const header = document.createElement("div");
      header.className = "tool-step-header";
      header.innerHTML = `
        <span class="tool-badge">🔧 ${step.tool}</span>
        <span class="tool-duration">${step.duration_ms}ms</span>
      `;
      
      const output = document.createElement("div");
      output.className = "tool-step-output";
      output.innerText = step.output;

      // Toggle output on click
      header.onclick = () => {
        output.style.display = output.style.display === "none" ? "block" : "none";
      };

      stepDiv.appendChild(header);
      stepDiv.appendChild(output);
      body.appendChild(stepDiv);
    });
  }

  const content = document.createElement("div");
  content.className = "msg-content";
  content.innerHTML = formatMarkdown(text);
  body.appendChild(content);

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(body);
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function showThinking() {
  const container = document.getElementById("chat-messages");
  const thinking = document.createElement("div");
  thinking.id = "thinking-indicator";
  thinking.className = "message agent-message";
  thinking.innerHTML = `
    <div class="msg-avatar">⚡</div>
    <div class="msg-body" style="color: var(--text-dim); font-style: italic;">
      Agent analyzing prompt and coordinating local tools...
    </div>
  `;
  container.appendChild(thinking);
  container.scrollTop = container.scrollHeight;
  document.getElementById("send-btn").disabled = true;
}

function hideThinking() {
  const thinking = document.getElementById("thinking-indicator");
  if (thinking) thinking.remove();
  document.getElementById("send-btn").disabled = false;
}

function formatMarkdown(text) {
  if (!text) return "";
  // Simple markdown converter (bold, code, links)
  let escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks
  escaped = escaped.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Bullet points
  escaped = escaped.replace(/^\s*[-•]\s+(.*)$/gm, '<li>$1</li>');
  
  return escaped;
}

// Safety Confirmation Modal
function showConfirmModal(action) {
  document.getElementById("modal-desc").innerText = action.warning || "Please confirm this action:";
  document.getElementById("modal-code").innerText = JSON.stringify(action, null, 2);
  document.getElementById("confirm-modal").classList.remove("hidden");
}

function closeConfirmModal() {
  document.getElementById("confirm-modal").classList.add("hidden");
  pendingActionData = null;
}

async function executeConfirmedAction() {
  if (!pendingActionData) return;
  
  const actionToExecute = { ...pendingActionData };
  closeConfirmModal();
  showThinking();

  try {
    const res = await fetch("/api/confirm-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: actionToExecute.tool,
        args: actionToExecute.args
      })
    });

    hideThinking();
    const data = await res.json();
    appendMessage("agent", `Action executed:\n\`\`\`\n${data.output || data.error}\n\`\`\``);
  } catch (err) {
    hideThinking();
    appendMessage("agent", `Error executing confirmed action: ${err.message}`);
  }
}
