# guest_management/pages/lucky_draw_hall.py
"""Presentation-only Lucky Draw hall/projector screen.

The operator remains authoritative. The hall receives the compact live draw
snapshot through the existing same-browser localStorage + BroadcastChannel
bridge.

The hall intentionally has:
- no operator controls
- no side ready-status card
- no decorative pointer/arrow
- no browser scrolling
- a single centered READY state inside the wheel
"""

import reflex as rx


_HALL_JS = r"""
(() => {
  const eventId = location.pathname.split('/').filter(Boolean).pop() || '';
  const storageKey = 'eventlah-lucky-draw-state:' + eventId;
  const channelName = 'eventlah-lucky-draw';

  const $ = (id) => document.getElementById(id);

  const root = $('eventlah-hall-root');
  const wheel = $('eventlah-hall-wheel');
  const wheelName = $('eventlah-hall-wheel-name');
  const wheelId = $('eventlah-hall-wheel-id');
  const wheelCaption = $('eventlah-hall-wheel-caption');
  const winner = $('eventlah-hall-winner');
  const winnerName = $('eventlah-hall-winner-name');
  const winnerId = $('eventlah-hall-winner-id');
  const winnerPrize = $('eventlah-hall-winner-prize');
  const winnerValue = $('eventlah-hall-winner-value');
  const doneScreen = $('eventlah-hall-done');
  const doneHistory = $('eventlah-hall-done-history');
  const eventName = $('eventlah-hall-event-name');
  const prizeName = $('eventlah-hall-prize-name');
  const prizeValue = $('eventlah-hall-prize-value');
  const prizeImage = $('eventlah-hall-prize-image');
  const progress = $('eventlah-hall-progress');
  const history = $('eventlah-hall-history');
  const connection = $('eventlah-hall-connection');

  if (!root) return;

  document.documentElement.style.background = '#000';
  document.body.style.margin = '0';
  document.body.style.background = '#000';
  document.body.style.overflow = 'hidden';
  document.body.style.cursor = 'none';

  function setImage(url) {
    if (url) {
      prizeImage.src = url;
      prizeImage.style.display = 'block';
    } else {
      prizeImage.removeAttribute('src');
      prizeImage.style.display = 'none';
    }
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));
  }

  function renderHistory(winners) {
    const list = Array.isArray(winners) ? winners : [];
    const html = list.length
      ? list.slice(0, 8).map((item, index) => `
          <div class="history-row">
            <div class="history-rank">${index + 1}</div>
            <div class="history-name">${escapeHtml(item.name || 'Winner')}</div>
            <div class="history-prize">${escapeHtml(item.prize_name || '')}</div>
            <div class="history-id">ID: ${escapeHtml(item.guest_id || '')}</div>
          </div>
        `).join('')
      : '<div class="empty-history">No winner confirmed yet</div>';

    if (history) history.innerHTML = html;
    if (doneHistory) doneHistory.innerHTML = html;
  }

  function visible(id, show) {
    const el = $(id);
    if (el) el.style.display = show ? '' : 'none';
  }

  function renderDone(state, prizeCount) {
    visible('eventlah-hall-main', false);
    visible('eventlah-hall-history', false);
    visible('eventlah-hall-footer', false);
    visible('eventlah-hall-done', true);

    const winners = Array.isArray(state.winners) ? state.winners : [];
    renderHistory(winners);

    const doneProgress = $('eventlah-hall-done-progress');
    if (doneProgress) {
      doneProgress.textContent = prizeCount > 0
        ? `${prizeCount} / ${prizeCount} prizes awarded`
        : 'All prizes awarded';
    }
  }

  function render(state) {
    if (!state || String(state.event_id || '') !== eventId) return;

    eventName.textContent = state.event_name || 'LUCKY DRAW';
    prizeName.textContent = state.prize_name || 'Lucky Draw';
    prizeValue.textContent = state.prize_value || '';
    prizeValue.style.display = state.prize_value ? 'inline-flex' : 'none';
    setImage(state.prize_picture || '');

    const prizeIndex = Number(state.prize_index || 0);
    const prizeCount = Number(state.prize_count || 0);
    progress.textContent = prizeCount ? `${prizeIndex + 1}/${prizeCount}` : '';

    const status = String(state.status || 'READY').toUpperCase();
    const spinning = status === 'DRAWING' || state.spinning === true;
    const candidate = status === 'CANDIDATE';
    const confirmed = status === 'CONFIRMED';
    const done = status === 'DONE';

    wheelName.textContent = state.current_name || 'READY';
    wheelId.textContent = state.current_id ? 'ID: ' + state.current_id : '';
    wheel.classList.toggle('spinning', spinning);
    if (wheelCaption) {
      wheelCaption.style.display = spinning ? 'block' : 'none';
    }

    if (done) {
      renderDone(state, prizeCount);
      return;
    }

    visible('eventlah-hall-done', false);
    visible('eventlah-hall-main', true);
    visible('eventlah-hall-history', true);
    visible('eventlah-hall-footer', true);

    if (candidate || confirmed) {
      wheel.style.display = 'none';
      winner.style.display = 'flex';
      winnerName.textContent = state.current_name || 'Winner';
      winnerId.textContent = state.current_id ? 'ID: ' + state.current_id : '';
      winnerPrize.textContent = 'Prize: ' + (state.prize_name || '');
      winnerValue.textContent = state.prize_value || '';
      winnerValue.style.display = state.prize_value ? 'inline-flex' : 'none';
    } else {
      wheel.style.display = 'flex';
      winner.style.display = 'none';
    }

    connection.textContent = '● LIVE';
    renderHistory(state.winners);
  }

  function loadStored() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) render(JSON.parse(raw));
    } catch (_) {}
  }

  loadStored();

  try {
    const channel = new BroadcastChannel(channelName);
    channel.addEventListener('message', (event) => render(event.data));
    window.addEventListener(
      'beforeunload',
      () => channel.close(),
      { once: true }
    );
  } catch (_) {}

  // Keep the display resilient to a dropped cross-tab message.
  window.setInterval(loadStored, 1200);
})();
"""

_CSS = r"""
<style>
html, body, #__next {
  margin: 0 !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 100% !important;
  overflow: hidden !important;
  background: #000 !important;
}

* {
  box-sizing: border-box;
}

#eventlah-hall-root {
  width: 100vw;
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
  background: #000;
  color: #fff;
  font-family: Arial, Helvetica, sans-serif;
}

.hall-shell {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) minmax(54px, 12dvh);
  padding: clamp(10px, 1.8vh, 22px) clamp(12px, 2.5vw, 36px);
  gap: clamp(8px, 1.2vh, 16px);
}

.hall-header {
  min-width: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  border-bottom: 1px solid rgba(212,175,55,.35);
  padding-bottom: clamp(8px, 1vh, 14px);
}

.hall-brand {
  color: #D4AF37;
  font-weight: 900;
  letter-spacing: .16em;
  font-size: clamp(18px, 1.8vw, 34px);
}

.hall-event-wrap {
  min-width: 0;
  text-align: right;
}

.hall-event {
  color: #fff;
  font-weight: 800;
  font-size: clamp(14px, 1.3vw, 24px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hall-live {
  color: #e74c3c;
  font-size: clamp(9px, .75vw, 15px);
  font-weight: 900;
  letter-spacing: .14em;
}

.hall-main {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, .82fr) minmax(0, 1.18fr);
  gap: clamp(10px, 1.7vw, 28px);
  align-items: stretch;
}

.hall-prize,
.hall-stage {
  min-width: 0;
  min-height: 0;
}

.hall-prize {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(5px, .7vh, 10px);
}

.hall-label {
  color: #D4AF37;
  font-size: clamp(9px, .75vw, 15px);
  font-weight: 900;
  letter-spacing: .16em;
}

.hall-prize-image {
  width: min(27vw, 30dvh, 390px);
  height: min(27dvh, 320px);
  object-fit: contain;
  border: 2px solid #D4AF37;
  border-radius: 16px;
  box-shadow: 0 0 28px rgba(212,175,55,.24);
  background: #050505;
}

.hall-prize-name {
  max-width: 100%;
  color: #F5D76E;
  font-size: clamp(20px, 2.35vw, 48px);
  font-weight: 900;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 0 16px rgba(212,175,55,.35);
}

.hall-prize-value {
  display: none;
  padding: 6px 12px;
  border-radius: 6px;
  background: #2d291d;
  color: #fff;
  font-weight: 800;
  font-size: clamp(11px, .9vw, 18px);
}

.hall-progress {
  color: #D4AF37;
  font-weight: 900;
  font-size: clamp(10px, .9vw, 18px);
}

.hall-stage {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hall-wheel {
  width: min(43vw, 52dvh, 640px); height: min(43vw, 52dvh, 640px);
  min-width: 0; min-height: 0;
  max-width: 100%;
  max-height: 100%;
  border-radius: 50%;
  border: clamp(5px, .65vw, 9px) solid #D4AF37;
  background: radial-gradient(
    circle,
    #050505 0 42%,
    #151515 43% 72%,
    #050505 73% 100%
  );
  box-shadow:
    0 0 42px rgba(212,175,55,.42),
    inset 0 0 28px rgba(212,175,55,.24);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.hall-wheel::before {
  content: '';
  position: absolute;
  inset: 7%;
  border: 2px solid rgba(212,175,55,.38);
  border-radius: 50%;
}

.hall-wheel.spinning {
  animation: wheelSpin .08s linear infinite;
}

@keyframes wheelSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hall-wheel-copy {
  position: relative;
  z-index: 2;
  max-width: 72%;
  text-align: center;
}

.hall-wheel-name {
  color: #F5D76E;
  font-weight: 900;
  font-size: clamp(22px, 3.2vw, 58px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 0 16px rgba(212,175,55,.75);
}

.hall-wheel-id {
  margin-top: 6px;
  color: #aaa;
  font-weight: 700;
  font-size: clamp(10px, .9vw, 18px);
}

.hall-caption {
  position: absolute;
  bottom: 4%;
  color: #D4AF37;
  font-size: clamp(10px, .95vw, 18px);
  font-weight: 900;
  letter-spacing: .18em;
}

.hall-winner {
  width: min(64vw, 720px);
  max-width: 100%;
  min-height: 0;
  max-height: 72%;
  border: 2px solid #D4AF37;
  border-radius: 20px;
  background: #707070;
  box-shadow: 0 0 30px rgba(212,175,55,.20);
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(7px, 1vh, 14px);
  padding: clamp(14px, 2.5vw, 34px);
  text-align: center;
}

.hall-winner-crown {
  color: #D4AF37;
  font-size: clamp(22px, 2vw, 40px);
}

.hall-winner-title {
  color: #F5D76E;
  font-size: clamp(18px, 1.8vw, 34px);
  font-weight: 900;
  letter-spacing: .08em;
}

.hall-winner-name {
  max-width: 90%;
  color: #fff;
  font-size: clamp(28px, 4vw, 70px);
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 0 20px rgba(212,175,55,.65);
}

.hall-winner-id {
  color: #fff;
  background: #777;
  padding: 6px 12px;
  border-radius: 5px;
  font-weight: 800;
  font-size: clamp(11px, 1vw, 18px);
}

.hall-winner-prize {
  color: #F5D76E;
  font-weight: 900;
  font-size: clamp(14px, 1.3vw, 25px);
}

.hall-history {
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
  border-top: 1px solid rgba(212,175,55,.35);
  padding-top: clamp(4px, .7vh, 9px);
}

.history-row {
  display: grid;
  grid-template-columns: 28px minmax(0, 1.2fr) minmax(0, 1fr) 100px;
  gap: 8px;
  align-items: center;
  padding: 4px 8px;
  border-bottom: 1px solid rgba(255,255,255,.07);
  font-size: clamp(9px, .68vw, 14px);
}

.history-rank { color: #D4AF37; font-weight: 900; }
.history-name,
.history-prize,
.history-id {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-name { color: #fff; font-weight: 800; }
.history-prize { color: #D4AF37; }
.history-id { color: #999; text-align: right; }

.empty-history {
  color: #777;
  text-align: center;
  padding: 8px;
  font-size: clamp(10px, .75vw, 15px);
}

.hall-done {
  min-height: 0;
  height: 100%;
  display: none;
  grid-template-columns: minmax(260px, .85fr) minmax(0, 1.15fr);
  gap: clamp(14px, 2vw, 32px);
  align-items: center;
  padding: clamp(10px, 1.5vw, 24px);
  overflow: hidden;
}

.hall-done-history {
  min-height: 0;
  max-height: 75%;
  overflow: hidden;
  border: 1px solid rgba(212,175,55,.35);
  border-radius: 16px;
  background: linear-gradient(145deg,#151515,#050505);
  padding: clamp(10px, 1.2vw, 18px);
}

.hall-done-history-title {
  color: #D4AF37;
  font-weight: 900;
  font-size: clamp(12px, 1vw, 20px);
  letter-spacing: .12em;
  margin-bottom: 8px;
}

.hall-done-history > div:last-child {
  max-height: calc(100% - 28px);
  overflow: hidden;
}

.hall-done-message {
  min-width: 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(8px, 1.2vh, 18px);
}

.hall-done-crown {
  color: #D4AF37;
  font-size: clamp(26px, 3vw, 54px);
}

.hall-done-title {
  color: #F5D76E;
  font-size: clamp(26px, 3.7vw, 60px);
  font-weight: 900;
  letter-spacing: .09em;
  text-shadow: 0 0 22px rgba(212,175,55,.45);
}

.hall-done-subtitle {
  color: #fff;
  font-size: clamp(14px, 1.2vw, 24px);
  font-weight: 800;
}

.hall-done-message-text {
  color: #999;
  font-size: clamp(11px, .9vw, 18px);
}

#eventlah-hall-footer {
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 900px) and (orientation: portrait) {
  .hall-shell {
    grid-template-rows: auto minmax(0, 1fr) minmax(62px, 15dvh);
    padding: 8px 10px;
    gap: 6px;
  }

  .hall-main {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 26dvh) minmax(0, 1fr);
    gap: 4px;
  }

  .hall-prize-image {
    width: min(38vw, 19dvh, 220px);
    height: min(19dvh, 190px);
  }

  .hall-wheel {
    width: min(72vw, 48dvh, 460px);
    height: min(72vw, 48dvh, 460px);
  }

  .hall-history {
    max-height: 100%;
  }

  .history-row {
    grid-template-columns: 22px minmax(0, 1.2fr) minmax(0, 1fr) 78px;
    gap: 5px;
    padding: 3px 5px;
  }

  .hall-done {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, .42fr) minmax(0, .58fr);
    gap: 8px;
  }

  .hall-done-history {
    max-height: 100%;
  }
}

/* EVENTLAH_RESPONSIVE_HALL_V2 */

html,
body,
#__next {
    width: 100% !important;
    height: 100% !important;
    margin: 0 !important;
    overflow: hidden !important;
}

#eventlah-hall-root {
    width: 100vw;
    height: 100dvh;
    min-height: 0;
    max-height: 100dvh;
    overflow: hidden !important;
}

.hall-shell {
    width: 100%;
    height: 100%;
    min-height: 0;
    max-height: 100%;
    overflow: hidden;
}

.hall-main {
    min-height: 0;
    overflow: hidden;
}

.hall-stage {
    min-height: 0;
    overflow: hidden;
}

.hall-wheel {
    width: min(43vw, 52dvh, 640px);
    height: min(43vw, 52dvh, 640px);
    min-width: 0;
    min-height: 0;
    max-width: 100%;
    max-height: 100%;
}

.hall-wheel-name {
    font-size: clamp(20px, 3.2vw, 58px);
}

.hall-winner-name {
    font-size: clamp(26px, 4vw, 70px);
}

.history-row {
    font-size: clamp(12px, 1.15vw, 24px);
    line-height: 1.15;
}

@media (max-height: 800px) {
    .hall-wheel {
        width: min(42vw, 46dvh, 560px);
        height: min(42vw, 46dvh, 560px);
    }

    .history-row {
        font-size: clamp(11px, 1vw, 19px);
    }
}

@media (max-height: 650px) {
    .hall-wheel {
        width: min(40vw, 42dvh, 480px);
        height: min(40vw, 42dvh, 480px);
    }

    .history-row {
        font-size: 11px;
    }
}
</style>
"""

def lucky_draw_hall_page():
    """Render the audience-only Lucky Draw hall screen."""
    return rx.box(
        rx.html(_CSS),
        rx.box(
            rx.box(
                rx.text("EVENTLAH", class_name="hall-brand"),
                rx.box(
                    rx.text(
                        "Lucky Draw",
                        id="eventlah-hall-event-name",
                        class_name="hall-event",
                    ),
                    rx.text(
                        "● LIVE",
                        id="eventlah-hall-connection",
                        class_name="hall-live",
                    ),
                    class_name="hall-event-wrap",
                ),
                class_name="hall-header",
            ),
            rx.box(
                rx.box(
                    rx.text("CURRENT PRIZE", class_name="hall-label"),
                    rx.image(
                        id="eventlah-hall-prize-image",
                        class_name="hall-prize-image",
                    ),
                    rx.text(
                        "Lucky Draw",
                        id="eventlah-hall-prize-name",
                        class_name="hall-prize-name",
                    ),
                    rx.text(
                        "",
                        id="eventlah-hall-prize-value",
                        class_name="hall-prize-value",
                    ),
                    rx.text(
                        "",
                        id="eventlah-hall-progress",
                        class_name="hall-progress",
                    ),
                    class_name="hall-prize",
                ),
                rx.box(
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "READY",
                                id="eventlah-hall-wheel-name",
                                class_name="hall-wheel-name",
                            ),
                            rx.text(
                                "",
                                id="eventlah-hall-wheel-id",
                                class_name="hall-wheel-id",
                            ),
                            align="center",
                            justify="center",
                            spacing="1",
                        ),
                        id="eventlah-hall-wheel",
                        class_name="hall-wheel",
                    ),
                    rx.text(
                        "🎲 SPINNING 🎲",
                        id="eventlah-hall-wheel-caption",
                        class_name="hall-caption",
                    ),
                    rx.box(
                        rx.text(
                            "✦  ♛  ✦",
                            class_name="hall-winner-crown",
                        ),
                        rx.text(
                            "WINNER!",
                            class_name="hall-winner-title",
                        ),
                        rx.text(
                            "",
                            id="eventlah-hall-winner-name",
                            class_name="hall-winner-name",
                        ),
                        rx.text(
                            "",
                            id="eventlah-hall-winner-id",
                            class_name="hall-winner-id",
                        ),
                        rx.text(
                            "",
                            id="eventlah-hall-winner-prize",
                            class_name="hall-winner-prize",
                        ),
                        rx.text(
                            "",
                            id="eventlah-hall-winner-value",
                            class_name="hall-prize-value",
                        ),
                        id="eventlah-hall-winner",
                        class_name="hall-winner",
                    ),
                    class_name="hall-stage",
                ),
                id="eventlah-hall-main",
                class_name="hall-main",
            ),
            rx.box(
                id="eventlah-hall-history",
                class_name="hall-history",
            ),
            rx.box(
                rx.box(
                    rx.box(
                        rx.text(
                            "WINNER HISTORY",
                            class_name="hall-done-history-title",
                        ),
                        rx.box(
                            id="eventlah-hall-done-history",
                        ),
                        class_name="hall-done-history",
                    ),
                    rx.box(
                        rx.text(
                            "✦  ♛  ✦",
                            class_name="hall-done-crown",
                        ),
                        rx.text(
                            "DRAW COMPLETE",
                            class_name="hall-done-title",
                        ),
                        rx.text(
                            "ALL PRIZES HAVE BEEN AWARDED",
                            class_name="hall-done-subtitle",
                        ),
                        rx.text(
                            "Thank you for joining us tonight.",
                            class_name="hall-done-message-text",
                        ),
                        rx.text(
                            "",
                            id="eventlah-hall-done-progress",
                            class_name="hall-progress",
                        ),
                        class_name="hall-done-message",
                    ),
                    id="eventlah-hall-done",
                    class_name="hall-done",
                ),
                id="eventlah-hall-footer",
            ),
            class_name="hall-shell",
        ),
        id="eventlah-hall-root",
        on_mount=rx.call_script(_HALL_JS),
    )
