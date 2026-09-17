# guest_management/pages/lucky_draw_display.py
"""
Fullscreen LIVE Lucky Draw presentation and operator control screen.

This is the MAIN prize draw screen.

It is intentionally separate from:
    guest_management/pages/pre_draw_display.py

The pre-draw screen shows preliminary winners only.

This screen controls the actual live prize draw:
    READY
        ↓
    DRAWING
        ↓
    CANDIDATE
        ↓
    CONFIRMED
        ↓
    NEXT PRIZE
        ↓
    DONE
"""

import reflex as rx

from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


# ============================================================================
# EVENT HEADER
# ============================================================================
def _event_header():
    """Render the EventLah live draw header."""
    return rx.hstack(
        rx.vstack(
            rx.text(
                "EVENTLAH",
                color=GOLD,
                font_size=["1.3em", "1.6em", "1.9em"],
                font_weight="900",
                letter_spacing="0.12em",
            ),
            rx.text(
                "LIVE LUCKY DRAW",
                color=LIGHT_GRAY,
                font_size=["0.55em", "0.65em", "0.72em"],
                font_weight="700",
                letter_spacing="0.16em",
            ),
            spacing="0",
            align="start",
        ),

        rx.button(
            rx.hstack(
                rx.icon(tag="monitor", size=16),
                rx.text("EXTERNAL SCREEN"),
                spacing="2",
            ),
            on_click=LuckyDrawState.open_hall_screen,
            variant="outline",
            border_color=GOLD,
            color=GOLD,
            size="2",
        ),

        rx.spacer(),

        rx.vstack(
            rx.text(
                "LIVE EVENT",
                color="white",
                font_size=["0.85em", "1em", "1.2em"],
                font_weight="800",
                text_align="right",
            ),
            rx.hstack(
                rx.box(
                    width="8px",
                    height="8px",
                    border_radius="50%",
                    background="red.500",
                ),
                rx.text(
                    "LIVE",
                    color="red.400",
                    font_size="0.65em",
                    font_weight="900",
                    letter_spacing="0.12em",
                ),
                spacing="2",
                align="center",
                justify="end",
            ),
            spacing="1",
            align="end",
        ),

        width="100%",
        align="center",
        padding_x=["0.5em", "1em"],
        padding_y=["0.5em", "0.75em"],
        border_bottom=f"1px solid {GOLD}40",
    )


def _wheel_styles():
    """Presentation CSS for the name-filled live wheel."""
    return rx.html(
        """<style>
        @keyframes eventlahNameWheelSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes eventlahNamePulse {
            0%, 100% { opacity: .72; }
            50% { opacity: 1; }
        }
        .eventlah-name-wheel {
            position: relative;
            width: min(76vw, 520px);
            height: min(76vw, 520px);
            min-width: 360px;
            min-height: 360px;
            border-radius: 50%;
            border: 8px solid #D4AF37;
            background: radial-gradient(circle, #151515 0 42%, #0b0b0b 43% 100%);
            box-shadow: 0 0 45px rgba(212,175,55,.35), inset 0 0 35px rgba(212,175,55,.20);
            overflow: hidden;
            will-change: transform;
        }
        .eventlah-name-wheel-spinning {
            animation: eventlahNameWheelSpin .55s linear infinite;
        }
        .eventlah-wheel-name-slot {
            color: #F5D76E;
            font-size: clamp(1rem, 1.7vw, 1.35rem);
            font-weight: 900;
            text-shadow: 0 0 12px rgba(212,175,55,.75);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .eventlah-wheel-center {
            position: absolute;
            inset: 50% auto auto 50%;
            transform: translate(-50%, -50%);
            width: 34%;
            height: 34%;
            border-radius: 50%;
            background: #050505;
            border: 4px solid #D4AF37;
            box-shadow: 0 0 28px rgba(212,175,55,.55);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 5;
        }
        .eventlah-wheel-center-name {
            color: #ffffff;
            font-size: clamp(1.05rem, 2vw, 1.7rem);
            font-weight: 900;
            text-align: center;
            max-width: 90%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .eventlah-wheel-center-id {
            color: #D4AF37;
            font-size: .85rem;
            font-weight: 700;
        }
        .eventlah-wheel-stage {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 570px;
            padding-top: 30px;
        }
        .eventlah-spinning-caption {
            position: absolute;
            bottom: 8px;
            color: #D4AF37;
            font-weight: 900;
            letter-spacing: .2em;
            animation: eventlahNamePulse 1s ease-in-out infinite;
        }
        </style>"""
    )


def _winner_card():
    """Render the video-style winner presentation for CANDIDATE/CONFIRMED."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="sparkles", size=28, color=GOLD),
                rx.icon(tag="crown", size=42, color=GOLD),
                rx.icon(tag="sparkles", size=28, color=GOLD),
                spacing="3",
                align="center",
                style={"animation": "bounce 0.5s ease-in-out"},
            ),
            rx.text(
                "WINNER!",
                color=GOLD,
                font_size=["1.2em", "1.45em", "1.7em"],
                font_weight="900",
                letter_spacing="0.08em",
                style={"animation": "pulse 0.8s ease-in-out"},
            ),
            rx.heading(
                LuckyDrawState.lucky_draw_current_name,
                size=rx.breakpoints(initial="6", md="7", lg="8"),
                color="white",
                weight="bold",
                text_align="center",
                style={
                    "textShadow": f"0 0 20px {GOLD}",
                    "animation": "scaleIn 0.5s ease-out",
                },
            ),
            rx.hstack(
                rx.badge(
                    "ID: " + LuckyDrawState.lucky_draw_current_id,
                    color_scheme="gold",
                    size="2",
                ),
                rx.badge(
                    rx.cond(
                        LuckyDrawState.draw_status == "CONFIRMED",
                        "CONFIRMED",
                        "CANDIDATE",
                    ),
                    color_scheme="gray",
                    size="2",
                ),
                spacing="2",
                justify="center",
            ),
            rx.divider(width="220px", border_color=GOLD),
            rx.text(
                "Prize: " + LuckyDrawState.lucky_draw_prize_name,
                color=GOLD,
                font_size=["1em", "1.15em", "1.35em"],
                font_weight="900",
                text_align="center",
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_prize_value != "",
                rx.badge(
                    "RM " + LuckyDrawState.lucky_draw_prize_value,
                    color_scheme="gold",
                    size="3",
                ),
                rx.fragment(),
            ),
            spacing="4",
            align="center",
            justify="center",
            padding=["1.5em", "2em", "2.5em"],
            width="100%",
            min_height=["360px", "430px", "500px"],
        ),
        background="#707070",
        border=f"1px solid {GOLD}",
        border_radius="18px",
        width="100%",
        min_height=["360px", "430px", "500px"],
        display="flex",
        align_items="center",
        justify_content="center",
        box_shadow=f"0 0 25px {GOLD}22",
    )


def _spinning_wheel():
    """Render the wheel/winner area exactly around the supplied video flow."""
    return rx.box(
        rx.cond(
            LuckyDrawState.lucky_draw_spinning,
            rx.vstack(
                rx.box(
                    rx.vstack(
                        rx.text(
                            rx.cond(
                                LuckyDrawState.lucky_draw_current_name != "",
                                LuckyDrawState.lucky_draw_current_name,
                                "Ready...",
                            ),
                            font_size=["1.5em", "1.8em", "2.1em"],
                            font_weight="900",
                            color=GOLD,
                            text_align="center",
                            max_width="80%",
                            overflow="hidden",
                            text_overflow="ellipsis",
                            white_space="nowrap",
                            style={"textShadow": f"0 0 12px {GOLD}"},
                        ),
                        rx.text(
                            "ID: " + LuckyDrawState.lucky_draw_current_id,
                            font_size="0.85em",
                            color="gray.300",
                            text_align="center",
                        ),
                        spacing="2",
                        align="center",
                        justify="center",
                        width="100%",
                        height="100%",
                    ),
                    width=["300px", "360px", "420px"],
                    height=["300px", "360px", "420px"],
                    border_radius="50%",
                    background=f"conic-gradient(from 0deg, {GOLD}33, {GOLD}66, {GOLD}99, {GOLD}CC, {GOLD}99, {GOLD}66, {GOLD}33)",
                    border=f"8px solid {GOLD}",
                    position="relative",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    style={
                        "animation": "wheelSpin 0.08s linear infinite",
                        "boxShadow": f"0 0 40px {GOLD}, inset 0 0 20px {GOLD}",
                        "backdropFilter": "blur(2px)",
                    },
                ),
                rx.text(
                    "🎲 SPINNING 🎲",
                    font_size=["1em", "1.15em", "1.3em"],
                    color=GOLD,
                    letter_spacing="0.2em",
                    margin_top="1.5em",
                    style={"animation": "pulse 1s ease-in-out infinite"},
                ),
                # Decorative Rings
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="50%",
                        bg=GOLD,
                        style={"animation": "pulse 0.5s ease-in-out infinite"},
                    ),
                    rx.box(
                        width="12px",
                        height="12px",
                        border_radius="50%",
                        bg=GOLD,
                        style={"animation": "pulse 0.5s ease-in-out infinite 0.1s"},
                    ),
                    rx.box(
                        width="6px",
                        height="6px",
                        border_radius="50%",
                        bg=GOLD,
                        style={"animation": "pulse 0.5s ease-in-out infinite 0.2s"},
                    ),
                    spacing="2",
                ),

                spacing="4",
                align="center",
                justify="center",
                width="100%",
                min_height=["420px", "500px", "570px"],
            ),

            rx.cond(
                (LuckyDrawState.draw_status == "CANDIDATE")
                | (LuckyDrawState.draw_status == "CONFIRMED"),
                _winner_card(),
                rx.vstack(
                    rx.box(
                        rx.icon(tag="gift", size=70, color=GOLD),
                        style={"animation": "float 3s ease-in-out infinite"},
                    ),
                    rx.heading("Ready to Draw!", size="5", color="white"),
                    rx.text(
                        LuckyDrawState.lucky_draw_eligible_count.to_string()
                        + " guests are eligible",
                        size="2",
                        color="gray",
                    ),
                    spacing="4",
                    align="center",
                    justify="center",
                    width="100%",
                    min_height=["420px", "500px", "570px"],
                ),
            ),
        ),
        width="100%",
        display="flex",
        align_items="center",
        justify_content="center",
    )

def _operator_controls():
    """All operator actions stay on the left side of the presentation."""
    return rx.vstack(
        rx.cond(
            LuckyDrawState.draw_status == "CANDIDATE",
            rx.vstack(
                rx.text(
                    "IS THIS PARTICIPANT PRESENT?",
                    color=LIGHT_GRAY,
                    font_size="0.78em",
                    font_weight="800",
                    letter_spacing="0.08em",
                    text_align="center",
                ),
                rx.hstack(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="circle_check", size=18),
                            rx.text("CONFIRM WINNER"),
                            spacing="2",
                        ),
                        on_click=LuckyDrawState.confirm_candidate,
                        background=GOLD,
                        color=BLACK,
                        size="3",
                        flex="1",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="user_x", size=18),
                            rx.text("ABSENT / REDRAW"),
                            spacing="2",
                        ),
                        on_click=LuckyDrawState.reject_candidate_as_absent,
                        variant="outline",
                        border_color="red.500",
                        color="red.400",
                        size="3",
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            rx.cond(
                LuckyDrawState.draw_status == "CONFIRMED",
                rx.button(
                    rx.hstack(
                        rx.icon(tag="chevron_right", size=20),
                        rx.text("NEXT PRIZE"),
                        spacing="2",
                    ),
                    on_click=LuckyDrawState.advance_to_next_prize,
                    background=GOLD,
                    color=BLACK,
                    size="3",
                    width="100%",
                    padding_y="1em",
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            (LuckyDrawState.draw_status != "CANDIDATE")
            & (LuckyDrawState.draw_status != "CONFIRMED"),
            rx.button(
                rx.hstack(
                    rx.icon(tag="play", size=21),
                    rx.text("START DRAW"),
                    spacing="2",
                ),
                on_click=LuckyDrawState.start_lucky_draw,
                background=GOLD,
                color=BLACK,
                size="4",
                width="100%",
                padding_y="1.15em",
                disabled=LuckyDrawState.lucky_draw_spinning,
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="3",
    )


def _current_prize():
    """Left-side operator panel: large prize image plus every operator action."""
    return rx.box(
        rx.vstack(
            rx.text(
                "CURRENT PRIZE",
                color=GOLD,
                font_size="0.75em",
                font_weight="900",
                letter_spacing="0.16em",
            ),
            rx.heading(
                LuckyDrawState.lucky_draw_prize_name,
                color="white",
                size=rx.breakpoints(initial="5", md="6", lg="7"),
                text_align="center",
                margin="0",
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_prize_value != "",
                rx.text(
                    LuckyDrawState.lucky_draw_prize_value,
                    color=GOLD,
                    font_size=["1em", "1.2em", "1.4em"],
                    font_weight="800",
                ),
                rx.fragment(),
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_prize_picture != "",
                rx.image(
                    src=LuckyDrawState.lucky_draw_prize_picture,
                    width="100%",
                    height=["260px", "330px", "390px"],
                    object_fit="contain",
                    border_radius="16px",
                    border=f"1px solid {GOLD}55",
                    background=BLACK,
                ),

                rx.box(
                    rx.icon(tag="gift", size=65, color=GOLD),
                    width="100%",
                    height=["260px", "330px", "390px"],
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    border=f"1px dashed {GOLD}",
                    border_radius="16px",
                ),
            ),
            rx.text(
                rx.cond(
                    LuckyDrawState.lucky_draw_spinning,
                    "DRAWING...",
                    rx.cond(
                        LuckyDrawState.draw_status == "CONFIRMED",
                        "WINNER CONFIRMED",
                        rx.cond(
                            LuckyDrawState.draw_status == "CANDIDATE",
                            "CANDIDATE SELECTED",
                            "READY FOR DRAW",
                        ),
                    ),
                ),
                color=rx.cond(LuckyDrawState.lucky_draw_spinning, GOLD, "white"),
                font_size="1.05em",
                font_weight="900",
                letter_spacing="0.08em",
            ),
            _operator_controls(),
            spacing="3",
            align="center",
            justify="center",
            width="100%",
        ),
        background=DARK_GRAY,
        border=f"2px solid {GOLD}",
        border_radius="20px",
        padding=["1.2em", "1.5em", "2em"],
        width="100%",
        min_height=["620px", "660px", "700px"],
        display="flex",
        align_items="center",
        justify_content="center",
    )


def _candidate_panel():
    """Right-side audience-only wheel/winner presentation."""
    return rx.box(
        rx.vstack(
            rx.text(
                "LIVE DRAW",
                color=GOLD,
                font_size="0.75em",
                font_weight="900",
                letter_spacing="0.16em",
            ),
            _spinning_wheel(),
            spacing="2",
            width="100%",
            align="center",
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="20px",
        padding=["1em", "1.25em", "1.5em"],
        width="100%",
        min_height=["620px", "660px", "700px"],
        display="flex",
        align_items="center",
        justify_content="center",
    )


# ============================================================================
# PRIZE PROGRESS
# ============================================================================

def _prize_progress():
    """Show the current prize position."""
    return rx.box(
        rx.hstack(
            rx.text(
                "PRIZE PROGRESS",
                color=GOLD,
                font_size="0.7em",
                font_weight="800",
                letter_spacing="0.1em",
            ),

            rx.spacer(),

            rx.text(
                rx.cond(
                    LuckyDrawState.current_prizes.length() > 0,
                    (
                        LuckyDrawState.current_prize_index + 1
                    ).to_string()
                    + " / "
                    + LuckyDrawState.current_prizes.length().to_string(),
                    "0 / 0",
                ),
                color="white",
                font_size="0.8em",
                font_weight="700",
            ),

            width="100%",
            align="center",
        ),

        rx.progress(
            value=(
                LuckyDrawState.current_prize_index + 1
            ),
            max=rx.cond(
                LuckyDrawState.current_prizes.length() > 0,
                LuckyDrawState.current_prizes.length(),
                1,
            ),
            width="100%",
            color_scheme="amber",
            margin_top="0.6em",
        ),

        background=DARK_GRAY,
        border_radius="10px",
        padding="0.8em",
        width="100%",
    )


# ============================================================================
# WINNER HISTORY
# ============================================================================

def _winner_history():
    """Always-visible live winner history."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon(tag="trophy", size=17, color=GOLD),
                rx.text("WINNER HISTORY", color=GOLD, font_size="0.72em", font_weight="800", letter_spacing="0.1em"),
                spacing="2",
            ),
            rx.spacer(),
            rx.text(LuckyDrawState.winners_list.length().to_string() + " confirmed", color=LIGHT_GRAY, font_size="0.72em"),
            rx.cond(
                LuckyDrawState.winners_list.length() > 0,
                rx.button(
                    "CLEAR HISTORY",
                    on_click=LuckyDrawState.clear_winners_history,
                    variant="outline",
                    border_color="red.500",
                    color="red.400",
                    size="1",
                ),
                rx.fragment(),
            ),
            width="100%",
            align="center",
        ),
        rx.cond(
            LuckyDrawState.winners_list.length() > 0,
            rx.grid(
                rx.foreach(
                    LuckyDrawState.winners_list[:10],
                    lambda winner: rx.box(
                        rx.vstack(
                            rx.text(winner.get("name", "Unknown"), color="white", font_size="0.85em", font_weight="800"),
                            rx.text(winner.get("prize_name", ""), color=GOLD, font_size="0.7em"),
                            spacing="0",
                            align="start",
                        ),
                        background=BLACK,
                        border_radius="8px",
                        padding="0.7em",
                        width="100%",
                    ),
                ),
                columns=rx.breakpoints(initial="1", md="2", lg="4"),
                spacing="2",
                width="100%",
                margin_top="0.7em",
            ),
            rx.text("No winner confirmed yet", color=LIGHT_GRAY, padding="1.5em", text_align="center", width="100%"),
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}40",
        border_radius="12px",
        padding="1em",
        width="100%",
    )


def _clear_history_dialog():
    """Confirmation dialog for clearing persisted winner history."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="triangle_alert", size=40, color="red"),
                rx.heading("Clear Winner History", size="5", color="red"),
                rx.text(
                    "Remove all confirmed winners for this event?",
                    color="white",
                    text_align="center",
                ),
                rx.text(
                    "This cannot be undone.",
                    color=LIGHT_GRAY,
                    size="2",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=LuckyDrawState.cancel_clear_winners,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                    ),
                    rx.button(
                        "Clear All",
                        on_click=LuckyDrawState.confirm_clear_winners,
                        background="red.500",
                        color="white",
                        flex="1",
                        disabled=LuckyDrawState.is_loading,
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
                align="center",
            ),
            background=DARK_GRAY,
            border="2px solid red",
            border_radius="15px",
            max_width="400px",
            width="90%",
        ),
        open=LuckyDrawState.show_clear_confirm,
    )


def _footer():
    """Render minimal navigation for the single synchronized draw screen."""
    return rx.hstack(
        rx.button(
            rx.hstack(
                rx.icon(tag="arrow_left", size=15),
                rx.text("BACK TO LUCKY DRAW"),
                spacing="2",
            ),
            on_click=rx.redirect(
                f"/lucky-draw/{LuckyDrawState.current_event_id}"
            ),
            variant="outline",
            border_color=GOLD,
            color=GOLD,
            size="2",
        ),
        rx.spacer(),
        rx.text(
            "ONE SCREEN • OPERATOR + AUDIENCE",
            color=LIGHT_GRAY,
            font_size="0.65em",
            letter_spacing="0.08em",
        ),
        width="100%",
        align="center",
    )


# ============================================================================
# EXTERNAL AUDIENCE DISPLAY
# ============================================================================

def lucky_draw_external_display_page():
    """Fullscreen audience-only window driven by the operator window."""
    sync_script = r"""
    (() => {
      const pathParts = window.location.pathname.split('/').filter(Boolean);
      const expectedEvent = decodeURIComponent(pathParts[pathParts.length - 1] || '');
      const channelName = 'eventlah-lucky-draw';
      const storageKey = 'eventlah-lucky-draw-state';

      const $ = (id) => document.getElementById(id);
      const setText = (id, value) => { const el = $(id); if (el) el.textContent = value ?? ''; };
      const setDisplay = (id, visible) => { const el = $(id); if (el) el.style.display = visible ? '' : 'none'; };

      function apply(state) {
        if (!state || String(state.event_id || '') !== expectedEvent) return;

        setText('ext-event', state.event_name || 'Lucky Draw');
        setText('ext-prize', state.prize_name || 'Prize');
        setText('ext-value', state.prize_value || '');
        setText('ext-wheel-name', state.current_name || 'Ready...');
        setText('ext-wheel-id', state.current_id ? 'ID: ' + state.current_id : '');
        setText('ext-winner-name', state.current_name || '');
        setText('ext-winner-id', state.current_id ? 'ID: ' + state.current_id : '');
        setText('ext-winner-prize', state.prize_name || '');
        setText('ext-progress', `${Number(state.prize_index || 0) + 1} / ${Number(state.prize_count || 0)}`);

        const image = $('ext-prize-image');
        if (image) {
          if (state.prize_picture) {
            image.src = state.prize_picture;
            image.style.display = '';
          } else {
            image.removeAttribute('src');
            image.style.display = 'none';
          }
        }

        const wheel = $('ext-wheel');
        if (wheel) wheel.classList.toggle('ext-spinning', !!state.spinning);

        const status = String(state.status || 'READY');
        setDisplay('ext-spinning-label', !!state.spinning);
        setDisplay('ext-winner-card', !state.spinning && (status === 'CANDIDATE' || status === 'CONFIRMED'));
        setDisplay('ext-ready-card', !state.spinning && status !== 'CANDIDATE' && status !== 'CONFIRMED');

        const confirmed = status === 'CONFIRMED';
        setText('ext-winner-status', confirmed ? 'WINNER CONFIRMED' : 'CANDIDATE SELECTED');

        const history = $('ext-history');
        if (history && Array.isArray(state.winners)) {
          history.replaceChildren();
          state.winners.slice(0, 10).forEach((winner, index) => {
            const row = document.createElement('div');
            row.className = 'ext-history-row';
            const left = document.createElement('span');
            left.textContent = `${index + 1}. ${winner.name || 'Winner'}`;
            const right = document.createElement('span');
            right.textContent = winner.prize_name || winner.prize || '';
            row.append(left, right);
            history.appendChild(row);
          });
        }
      }

      try {
        const cached = localStorage.getItem(storageKey);
        if (cached) apply(JSON.parse(cached));
      } catch (_) {}

      try {
        const channel = new BroadcastChannel(channelName);
        channel.onmessage = (event) => apply(event.data);
        window.addEventListener('beforeunload', () => channel.close(), { once: true });
      } catch (_) {}
    })();
    """

    styles = """
    <style>
      html, body, #__next { margin:0; width:100%; min-height:100%; background:#000; color:#fff; }
      .ext-screen { min-height:100vh; width:100vw; box-sizing:border-box; background:#050505; display:flex; flex-direction:column; font-family:Inter,Arial,sans-serif; }
      .ext-header { padding:18px 28px; border-bottom:1px solid rgba(212,175,55,.35); text-align:center; }
      .ext-event { color:#D4AF37; font-size:clamp(18px,2vw,32px); font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
      .ext-content { flex:1; display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.2fr); gap:28px; padding:28px; box-sizing:border-box; }
      .ext-prize-panel,.ext-live-panel { background:#151515; border:1px solid rgba(212,175,55,.45); border-radius:22px; padding:24px; box-sizing:border-box; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:calc(100vh - 170px); }
      .ext-label { color:#D4AF37; font-size:12px; font-weight:900; letter-spacing:.18em; }
      .ext-prize { margin-top:8px; color:#fff; font-size:clamp(24px,3vw,48px); font-weight:900; text-align:center; }
      .ext-value { color:#D4AF37; font-size:clamp(18px,2vw,30px); font-weight:800; margin:8px 0 18px; }
      .ext-prize-image { width:100%; max-width:620px; height:min(48vh,500px); object-fit:contain; border-radius:18px; border:1px solid rgba(212,175,55,.4); background:#050505; }
      .ext-wheel-wrap { display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%; gap:18px; }
      .ext-wheel { width:min(52vw,560px); height:min(52vw,560px); min-width:330px; min-height:330px; border-radius:50%; border:9px solid #D4AF37; background:radial-gradient(circle,#151515 0 40%,#090909 41% 100%); box-shadow:0 0 55px rgba(212,175,55,.35), inset 0 0 35px rgba(212,175,55,.18); display:flex; align-items:center; justify-content:center; position:relative; }
      .ext-wheel:before { content:''; position:absolute; top:-28px; left:50%; transform:translateX(-50%); border-left:18px solid transparent; border-right:18px solid transparent; border-top:32px solid #D4AF37; filter:drop-shadow(0 0 7px rgba(212,175,55,.7)); }
      .ext-wheel.ext-spinning { animation:extWheelSpin .10s linear infinite; }
      .ext-name { max-width:80%; color:#D4AF37; font-size:clamp(26px,4vw,64px); font-weight:900; text-align:center; text-shadow:0 0 18px rgba(212,175,55,.8); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .ext-id { margin-top:8px; color:#bbb; font-size:clamp(14px,1.5vw,22px); }
      .ext-spin-label { color:#D4AF37; font-weight:900; letter-spacing:.2em; animation:extPulse 1s ease-in-out infinite; }
      .ext-card { width:min(90%,760px); min-height:340px; border:1px solid #D4AF37; border-radius:22px; background:#707070; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:28px; box-sizing:border-box; box-shadow:0 0 35px rgba(212,175,55,.15); text-align:center; }
      .ext-card .crown { color:#D4AF37; font-size:58px; margin-bottom:10px; }
      .ext-card .winner { color:#D4AF37; font-size:clamp(24px,3vw,42px); font-weight:900; letter-spacing:.08em; }
      .ext-card .winner-name { color:#fff; font-size:clamp(34px,5vw,72px); font-weight:900; margin:12px 0; text-shadow:0 0 18px #D4AF37; }
      .ext-card .winner-prize { color:#D4AF37; font-size:clamp(18px,2vw,28px); font-weight:900; }
      .ext-ready { color:#fff; text-align:center; }
      .ext-ready .icon { color:#D4AF37; font-size:80px; }
      .ext-ready h2 { font-size:clamp(24px,3vw,40px); margin:18px 0 8px; }
      .ext-ready p { color:#aaa; font-size:clamp(15px,1.5vw,22px); }
      .ext-bottom { padding:14px 28px 22px; border-top:1px solid rgba(212,175,55,.25); }
      .ext-progress-head { display:flex; justify-content:space-between; color:#aaa; font-size:13px; }
      .ext-history { margin-top:8px; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px 18px; max-height:130px; overflow:hidden; }
      .ext-history-row { display:flex; justify-content:space-between; gap:12px; color:#ddd; font-size:13px; padding:6px 0; border-bottom:1px solid #222; }
      .ext-history-row span:last-child { color:#D4AF37; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      @keyframes extWheelSpin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
      @keyframes extPulse { 0%,100%{opacity:.65} 50%{opacity:1} }
      @media (max-width:900px) { .ext-content { grid-template-columns:1fr; } .ext-prize-panel,.ext-live-panel { min-height:auto; } .ext-prize-image { height:35vh; } .ext-wheel { width:min(78vw,500px); height:min(78vw,500px); } }
    </style>
    """

    return rx.box(
        rx.html(styles),
        rx.vstack(
            rx.box(rx.text("Lucky Draw", id="ext-event", class_name="ext-event"), class_name="ext-header", width="100%"),
            rx.box(
                rx.box(
                    rx.text("CURRENT PRIZE", class_name="ext-label"),
                    rx.text("Prize", id="ext-prize", class_name="ext-prize"),
                    rx.text("", id="ext-value", class_name="ext-value"),
                    rx.image(id="ext-prize-image", display="none", class_name="ext-prize-image"),
                    width="100%", class_name="ext-prize-panel",
                ),
                rx.box(
                    rx.text("LIVE DRAW", class_name="ext-label"),
                    rx.box(
                        rx.box(
                            rx.text("Ready...", id="ext-wheel-name", class_name="ext-name"),
                            rx.text("", id="ext-wheel-id", class_name="ext-id"),
                            id="ext-wheel", class_name="ext-wheel",
                        ),
                        rx.text("DRAWING...", id="ext-spinning-label", class_name="ext-spin-label", display="none"),
                        rx.box(
                            rx.text("♛", class_name="crown"),
                            rx.text("WINNER!", class_name="winner"),
                            rx.text("", id="ext-winner-name", class_name="winner-name"),
                            rx.text("", id="ext-winner-id", class_name="ext-id"),
                            rx.text("", id="ext-winner-prize", class_name="winner-prize"),
                            rx.text("", id="ext-winner-status", class_name="ext-value"),
                            id="ext-winner-card", class_name="ext-card", display="none",
                        ),
                        rx.box(
                            rx.text("✦", class_name="icon"),
                            rx.heading("Ready to Draw!", size="5"),
                            rx.text("The next prize is ready.", size="2"),
                            id="ext-ready-card", class_name="ext-ready", display="",
                        ),
                        width="100%", class_name="ext-wheel-wrap",
                    ),
                    width="100%", class_name="ext-live-panel",
                ),
                class_name="ext-content", width="100%",
            ),
            rx.box(
                rx.box(
                    rx.text("PRIZE PROGRESS", class_name="ext-label"),
                    rx.text("0 / 0", id="ext-progress"),
                    class_name="ext-progress-head",
                ),
                rx.box(id="ext-history", class_name="ext-history"),
                class_name="ext-bottom", width="100%",
            ),
            spacing="0", width="100%", min_height="100vh",
        ),
        width="100%", min_height="100vh", background="#050505",
        on_mount=rx.call_script(sync_script),
    )

# ============================================================================
# MAIN PAGE
# ============================================================================

def lucky_draw_display_page():
    """
    Render the MAIN live Lucky Draw display.

    This is the screen opened by:
        START DISPLAY SCREEN
    """
    return rx.box(
        _wheel_styles(),
        rx.vstack(
            _event_header(),

            # -----------------------------------------------------------
            # CURRENT PRIZE + DRAW RESULT
            # -----------------------------------------------------------
            rx.grid(
                _current_prize(),
                _candidate_panel(),
                columns=rx.breakpoints(initial="1", lg="repeat(2, minmax(0, 1fr))"),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),

            _prize_progress(),
            _winner_history(),
            _clear_history_dialog(),

            _footer(),

            spacing="4",
            width="100%",
            max_width="1800px",
            padding=[
                "1em",
                "1.5em",
                "2em",
            ],
        ),

        background=BLACK,
        min_height="100vh",
        width="100%",
        color="white",
    )
