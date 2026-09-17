# guest_management/pages/lucky_draw_hall.py
"""Cursor-free fullscreen Lucky Draw audience window.

The operator window remains the only interactive control surface.  This page is
presentation-only and receives the authoritative live snapshot through the
same-browser BroadcastChannel/localStorage bridge.
"""

import reflex as rx


_HALL_JS = r"""
(() => {
  const eventId = location.pathname.split('/').filter(Boolean).pop() || '';
  const storageKey = 'eventlah-lucky-draw-state:' + eventId;
  const channelName = 'eventlah-lucky-draw';

  const root = document.getElementById('eventlah-hall-root');
  const wheel = document.getElementById('eventlah-hall-wheel');
  const wheelName = document.getElementById('eventlah-hall-wheel-name');
  const wheelId = document.getElementById('eventlah-hall-wheel-id');
  const wheelCaption = document.getElementById('eventlah-hall-wheel-caption');
  const winner = document.getElementById('eventlah-hall-winner');
  const winnerName = document.getElementById('eventlah-hall-winner-name');
  const winnerId = document.getElementById('eventlah-hall-winner-id');
  const winnerPrize = document.getElementById('eventlah-hall-winner-prize');
  const winnerValue = document.getElementById('eventlah-hall-winner-value');
  const ready = document.getElementById('eventlah-hall-ready');
  const eventName = document.getElementById('eventlah-hall-event-name');
  const prizeName = document.getElementById('eventlah-hall-prize-name');
  const prizeValue = document.getElementById('eventlah-hall-prize-value');
  const prizeImage = document.getElementById('eventlah-hall-prize-image');
  const progress = document.getElementById('eventlah-hall-progress');
  const history = document.getElementById('eventlah-hall-history');
  const connection = document.getElementById('eventlah-hall-connection');

  if (!root) return;

  document.documentElement.style.background = '#000';
  document.body.style.margin = '0';
  document.body.style.background = '#000';
  document.body.style.overflow = 'hidden';
  document.body.style.cursor = 'none';

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[c]));

  function setImage(url) {
    if (url) {
      prizeImage.src = url;
      prizeImage.style.display = 'block';
    } else {
      prizeImage.removeAttribute('src');
      prizeImage.style.display = 'none';
    }
  }

  function renderHistory(winners) {
    const list = Array.isArray(winners) ? winners : [];
    if (!list.length) {
      history.innerHTML = '<div class="empty-history">No winner confirmed yet</div>';
      return;
    }
    history.innerHTML = list.slice(0, 8).map((item, index) => `
      <div class="history-row">
        <div class="history-rank">${index + 1}</div>
        <div class="history-name">${esc(item.name || 'Winner')}</div>
        <div class="history-prize">${esc(item.prize_name || '')}</div>
        <div class="history-id">ID: ${esc(item.guest_id || '')}</div>
      </div>
    `).join('');
  }

  function render(payload) {
    if (!payload || String(payload.event_id || '') !== eventId) return;

    eventName.textContent = payload.event_name || 'LUCKY DRAW';
    prizeName.textContent = payload.prize_name || 'Lucky Draw';
    prizeValue.textContent = payload.prize_value || '';
    prizeValue.style.display = payload.prize_value ? 'inline-flex' : 'none';
    setImage(payload.prize_picture || '');

    const prizeIndex = Number(payload.prize_index || 0) + 1;
    const prizeCount = Number(payload.prize_count || 0);
    progress.textContent = prizeCount ? `${prizeIndex}/${prizeCount}` : '';

    const spinning = payload.status === 'DRAWING' || payload.spinning === true;
    const candidate = payload.status === 'CANDIDATE';
    const confirmed = payload.status === 'CONFIRMED';

    wheelName.textContent = payload.current_name || 'Ready...';
    wheelId.textContent = payload.current_id ? 'ID: ' + payload.current_id : 'ID: ...';
    wheel.classList.toggle('spinning', spinning);
    wheelCaption.style.display = spinning ? 'block' : 'none';

    if (candidate || confirmed) {
      wheel.style.display = 'none';
      ready.style.display = 'none';
      winner.style.display = 'flex';
      winnerName.textContent = payload.current_name || 'Winner';
      winnerId.textContent = payload.current_id ? 'ID: ' + payload.current_id : '';
      winnerPrize.textContent = 'Prize: ' + (payload.prize_name || '');
      winnerValue.textContent = payload.prize_value || '';
      winnerValue.style.display = payload.prize_value ? 'inline-flex' : 'none';
    } else {
      winner.style.display = 'none';
      ready.style.display = spinning ? 'none' : 'flex';
      wheel.style.display = 'flex';
    }

    connection.textContent = '● LIVE';
    renderHistory(payload.winners);
  }

  function loadStored() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) render(JSON.parse(raw));
    } catch (e) {}
  }

  loadStored();

  try {
    const channel = new BroadcastChannel(channelName);
    channel.addEventListener('message', event => render(event.data));
    window.addEventListener('beforeunload', () => channel.close());
  } catch (e) {}

  // Keep the hall display resilient if the browser suppresses a BroadcastChannel
  // message during a tab/window transition.
  window.setInterval(loadStored, 1000);

  // Best-effort browser fullscreen. Browsers may require the user to press F11
  // or allow fullscreen manually; CSS itself is already viewport-fullscreen.
  window.addEventListener('load', () => {
    setTimeout(() => {
      try {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen?.().catch(() => {});
        }
      } catch (e) {}
    }, 400);
  });
})();
"""

_CSS = r"""
<style>
html, body { background:#000 !important; }
* { box-sizing:border-box; }
#eventlah-hall-root {
  width:100vw; height:100vh; min-height:100vh; overflow:hidden;
  background:#000; color:#fff; font-family:Arial, Helvetica, sans-serif;
}
.hall-shell { width:100%; height:100%; display:flex; flex-direction:column; padding:2.2vh 3vw; }
.hall-header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(212,175,55,.35); padding-bottom:1.2vh; }
.hall-brand { color:#D4AF37; font-weight:900; letter-spacing:.16em; font-size:clamp(18px,1.7vw,34px); }
.hall-event { color:#fff; font-weight:800; font-size:clamp(16px,1.4vw,28px); text-align:right; }
.hall-live { color:#e74c3c; font-size:clamp(10px,.8vw,16px); font-weight:900; letter-spacing:.14em; }
.hall-main { flex:1; min-height:0; display:grid; grid-template-columns:minmax(280px,.8fr) minmax(480px,1.2fr); gap:3vw; align-items:center; }
.hall-prize { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:0; }
.hall-label { color:#D4AF37; font-size:clamp(10px,.8vw,16px); font-weight:900; letter-spacing:.16em; }
.hall-prize-image { width:min(28vw,420px); height:min(30vh,360px); object-fit:contain; border:2px solid #D4AF37; border-radius:18px; margin:1.2vh 0; box-shadow:0 0 32px rgba(212,175,55,.28); background:#050505; }
.hall-prize-name { color:#F5D76E; font-size:clamp(24px,2.6vw,54px); font-weight:900; text-align:center; text-shadow:0 0 18px rgba(212,175,55,.35); }
.hall-prize-value, .hall-winner-value { display:inline-flex; padding:7px 14px; border-radius:6px; background:#2d291d; color:#fff; font-weight:800; font-size:clamp(12px,1vw,20px); }
.hall-progress { margin-top:1vh; color:#D4AF37; font-weight:900; font-size:clamp(12px,1vw,20px); }
.hall-stage { position:relative; width:100%; min-height:0; height:72vh; display:flex; align-items:center; justify-content:center; }
.hall-wheel {
  width:min(48vw,620px); height:min(48vw,620px); min-width:360px; min-height:360px;
  border-radius:50%; border:9px solid #D4AF37;
  background:radial-gradient(circle,#050505 0 42%,#151515 43% 72%,#050505 73% 100%);
  box-shadow:0 0 50px rgba(212,175,55,.48), inset 0 0 30px rgba(212,175,55,.25);
  display:flex; align-items:center; justify-content:center; position:relative;
}
.hall-wheel.spinning { animation:wheelSpin .08s linear infinite; }
@keyframes wheelSpin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
.hall-wheel::before { content:''; position:absolute; inset:7%; border:2px solid rgba(212,175,55,.38); border-radius:50%; }
.hall-wheel-name { color:#F5D76E; font-weight:900; font-size:clamp(24px,3.2vw,58px); max-width:72%; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; text-shadow:0 0 16px rgba(212,175,55,.75); }
.hall-wheel-id { color:#aaa; font-weight:700; font-size:clamp(12px,1vw,20px); margin-top:8px; }
.hall-pointer { position:absolute; top:1%; left:50%; transform:translateX(-50%); width:0; height:0; border-left:18px solid transparent; border-right:18px solid transparent; border-top:36px solid #D4AF37; z-index:10; filter:drop-shadow(0 0 8px rgba(212,175,55,.8)); }
.hall-caption { position:absolute; bottom:7%; color:#D4AF37; font-size:clamp(12px,1.2vw,24px); font-weight:900; letter-spacing:.2em; }
.hall-ready { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:1.5vh; text-align:center; }
.hall-ready-title { color:#fff; font-weight:900; font-size:clamp(24px,2.5vw,48px); }
.hall-ready-sub { color:#aaa; font-size:clamp(13px,1vw,20px); }
.hall-winner {
  width:min(62vw,720px); min-height:42vh; border:2px solid #D4AF37; border-radius:20px;
  background:#707070; box-shadow:0 0 36px rgba(212,175,55,.22);
  display:none; flex-direction:column; align-items:center; justify-content:center; gap:1.3vh; padding:4vh 4vw; text-align:center;
}
.hall-winner-crown { color:#D4AF37; font-size:clamp(24px,2.5vw,46px); }
.hall-winner-title { color:#F5D76E; font-size:clamp(20px,2vw,38px); font-weight:900; letter-spacing:.08em; }
.hall-winner-name { color:#fff; font-size:clamp(34px,4vw,76px); font-weight:900; text-shadow:0 0 20px rgba(212,175,55,.65); }
.hall-winner-id { color:#fff; background:#777; padding:6px 12px; border-radius:5px; font-weight:800; font-size:clamp(12px,1vw,20px); }
.hall-winner-prize { color:#F5D76E; font-weight:900; font-size:clamp(16px,1.4vw,28px); }
.hall-history { border-top:1px solid rgba(212,175,55,.35); padding-top:1vh; min-height:8vh; max-height:15vh; overflow:hidden; }
.history-row { display:grid; grid-template-columns:40px 1.2fr 1fr 120px; gap:10px; align-items:center; padding:5px 10px; border-bottom:1px solid rgba(255,255,255,.07); font-size:clamp(10px,.75vw,15px); }
.history-rank { color:#D4AF37; font-weight:900; }
.history-name { color:#fff; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.history-prize { color:#D4AF37; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.history-id { color:#999; text-align:right; }
.empty-history { color:#777; text-align:center; padding:1.2vh; font-size:clamp(11px,.8vw,16px); }
@media (max-width:900px) { .hall-main { grid-template-columns:1fr; overflow:auto; } .hall-shell { overflow:auto; } .hall-stage { height:55vh; } .hall-prize-image { width:35vw; height:22vh; } }
</style>
"""


def lucky_draw_hall_page():
    """Render the presentation-only hall screen."""
    return rx.box(
        rx.html(_CSS),
        rx.box(
            rx.box(
                rx.text("EVENTLAH", class_name="hall-brand"),
                rx.box(
                    rx.text("LIVE EVENT", class_name="hall-event"),
                    rx.text("● LIVE", id="eventlah-hall-connection", class_name="hall-live"),
                    class_name="hall-event-wrap",
                ),
                class_name="hall-header",
            ),
            rx.box(
                rx.box(
                    rx.text("CURRENT PRIZE", class_name="hall-label"),
                    rx.image(id="eventlah-hall-prize-image", class_name="hall-prize-image"),
                    rx.text("Lucky Draw", id="eventlah-hall-prize-name", class_name="hall-prize-name"),
                    rx.text("", id="eventlah-hall-prize-value", class_name="hall-prize-value"),
                    rx.text("", id="eventlah-hall-progress", class_name="hall-progress"),
                    class_name="hall-prize",
                ),
                rx.box(
                    rx.box(class_name="hall-pointer"),
                    rx.box(
                        rx.vstack(
                            rx.text("Ready...", id="eventlah-hall-wheel-name", class_name="hall-wheel-name"),
                            rx.text("ID: ...", id="eventlah-hall-wheel-id", class_name="hall-wheel-id"),
                            align="center",
                            justify="center",
                        ),
                        id="eventlah-hall-wheel",
                        class_name="hall-wheel",
                    ),
                    rx.text("🎲 SPINNING 🎲", id="eventlah-hall-wheel-caption", class_name="hall-caption"),
                    rx.box(
                        rx.text("READY FOR DRAW", class_name="hall-ready-title"),
                        rx.text("The next winner will appear here.", class_name="hall-ready-sub"),
                        id="eventlah-hall-ready",
                        class_name="hall-ready",
                    ),
                    rx.box(
                        rx.text("✦  ♛  ✦", class_name="hall-winner-crown"),
                        rx.text("WINNER!", class_name="hall-winner-title"),
                        rx.text("", id="eventlah-hall-winner-name", class_name="hall-winner-name"),
                        rx.text("", id="eventlah-hall-winner-id", class_name="hall-winner-id"),
                        rx.text("", id="eventlah-hall-winner-prize", class_name="hall-winner-prize"),
                        rx.text("", id="eventlah-hall-winner-value", class_name="hall-winner-value"),
                        id="eventlah-hall-winner",
                        class_name="hall-winner",
                    ),
                    class_name="hall-stage",
                ),
                class_name="hall-main",
            ),
            rx.box(id="eventlah-hall-history", class_name="hall-history"),
            class_name="hall-shell",
        ),
        id="eventlah-hall-root",
        on_mount=rx.call_script(_HALL_JS),
    )
