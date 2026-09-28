const $ = (selector) => document.querySelector(selector);
const base = (window.APP_CONFIG?.API_BASE_URL || "").replace(/\/$/, "");
let conversationId = null;
let editingId = null;
let busy = false;

function notice(message) { $("#notice").textContent = message; }
function element(tag, text, className = "") {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
}
async function api(path, options = {}) {
  const response = await fetch(base + path, { ...options, headers: { "Content-Type": "application/json" } });
  if (response.status === 204) return null;
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "요청에 실패했습니다.");
  return payload;
}
function showView(name) {
  if (busy) return;
  document.querySelectorAll(".view").forEach((node) => node.hidden = node.id !== `view-${name}`);
  document.querySelectorAll("nav button").forEach((node) => node.classList.toggle("active", node.dataset.view === name));
}
function renderMessages(messages) {
  $("#messages").replaceChildren();
  if (!messages.length) $("#messages").append(element("p", "학습 기록에 대해 질문해보세요.", "empty"));
  for (const message of messages) {
    const box = element("div", "", `message ${message.role}`);
    box.append(element("small", message.role === "user" ? "나" : "AI 비서"), element("p", message.content));
    $("#messages").append(box);
  }
  $("#messages").scrollTop = $("#messages").scrollHeight;
}
async function refreshData() {
  const [rows, summary] = await Promise.all([api("/api/data"), api("/api/data/summary")]);
  $("#period").textContent = summary.period || "데이터 없음";
  $("#count").textContent = `${summary.count}개`;
  $("#average").textContent = summary.metrics ? `${summary.metrics.average}분` : "—";
  $("#trend").textContent = summary.trend + (summary.change_percent == null ? "" : ` (${summary.change_percent > 0 ? "+" : ""}${summary.change_percent}%)`);
  $("#data-rows").replaceChildren();
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.append(element("td", row.date), element("td", `${row.value}분`), element("td", row.memo || "—"));
    const actions = document.createElement("td");
    const edit = element("button", "수정", "small secondary");
    edit.type = "button";
    edit.onclick = () => { editingId = row.id; $("#date").value = row.date; $("#value").value = row.value; $("#memo").value = row.memo; $("#save-data").textContent = "저장"; $("#cancel-edit").hidden = false; };
    const remove = element("button", "삭제", "small danger");
    remove.type = "button";
    remove.onclick = async () => { if (!confirm("이 기록을 삭제할까요?")) return; try { await api(`/api/data/${row.id}`, { method: "DELETE" }); await refreshData(); notice("기록을 삭제했습니다."); } catch (error) { notice(error.message); } };
    actions.append(edit, remove); tr.append(actions); $("#data-rows").append(tr);
  }
  if (!rows.length) { const td = element("td", "아직 데이터가 없습니다.", "empty"); td.colSpan = 4; const tr = document.createElement("tr"); tr.append(td); $("#data-rows").append(tr); }
}
function resetForm() {
  editingId = null; $("#data-form").reset(); $("#date").value = new Date().toLocaleDateString("en-CA"); $("#save-data").textContent = "추가"; $("#cancel-edit").hidden = true;
}
async function refreshHistory() {
  const items = await api("/api/conversations"); $("#history-list").replaceChildren();
  if (!items.length) $("#history-list").append(element("p", "저장된 대화가 없습니다.", "empty padded"));
  for (const item of items) {
    const row = element("div", "", "history-item");
    const load = element("button", "", "history-load secondary"); load.append(element("strong", item.title), element("small", new Date(item.updated_at).toLocaleString("ko-KR")));
    load.onclick = async () => { try { const data = await api(`/api/conversations/${item.id}`); conversationId = data.id; renderMessages(data.messages); showView("chat"); notice("이전 대화를 불러왔습니다."); } catch (error) { notice(error.message); } };
    const remove = element("button", "삭제", "small danger"); remove.onclick = async () => { if (!confirm("이 대화를 삭제할까요?")) return; try { await api(`/api/conversations/${item.id}`, { method: "DELETE" }); if (conversationId === item.id) { conversationId = null; renderMessages([]); } await refreshHistory(); } catch (error) { notice(error.message); } };
    row.append(load, remove); $("#history-list").append(row);
  }
}

$("#data-form").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api(editingId ? `/api/data/${editingId}` : "/api/data", { method: editingId ? "PUT" : "POST", body: JSON.stringify({ date: $("#date").value, value: Number($("#value").value), memo: $("#memo").value }) });
    resetForm(); await refreshData(); notice("데이터와 요약을 갱신했습니다.");
  } catch (error) { notice(error.message); }
};
$("#cancel-edit").onclick = resetForm;
$("#chat-form").onsubmit = async (event) => {
  event.preventDefault(); const question = $("#question").value.trim(); if (!question || busy) return;
  busy = true; $("#send").disabled = true; $("#send").textContent = "답변 생성 중…"; notice("데이터 요약을 확인하고 있습니다.");
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: question, conversation_id: conversationId }) });
    conversationId = result.conversation_id; renderMessages(result.messages); $("#question").value = "";
    notice(result.usage?.mode === "mock" ? "연습 모드: 사용 토큰 0" : `답변 저장 완료 · ${result.usage?.total_tokens || "사용량 확인 불가"} 토큰`);
    await refreshHistory();
  } catch (error) { notice(error.message); }
  finally { busy = false; $("#send").disabled = false; $("#send").textContent = "보내기"; }
};
$("#new-chat").onclick = () => { conversationId = null; renderMessages([]); notice("새 대화를 시작합니다."); };
document.querySelectorAll("nav button").forEach((button) => button.onclick = () => showView(button.dataset.view));

async function initialize() {
  try {
    const health = await api("/health");
    $("#mode").textContent = health.ai_mode === "mock" ? "연습 모드 · 토큰 0" : "OpenAI 연결 모드";
    await Promise.all([refreshData(), refreshHistory()]);
    notice("연결되었습니다. 먼저 예시 데이터를 불러오거나 직접 기록을 추가하세요.");
  } catch (error) { notice(error.message); }
}
resetForm(); initialize();

