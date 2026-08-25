import reflex as rx

from guest_management.pages import page_layout
from guest_management.styles.theme import button_style, card_style, GOLD, BLACK



def feature_card(icon: str, title: str, description: str):
    """Feature card with consistent sizing."""
    return rx.vstack(
        rx.hstack(
            rx.cond(
                rx.breakpoints(sm=False, md=False, lg=False, xl=False),
                rx.icon(tag=icon, size=14, color=GOLD),  # Mobile
                rx.cond(
                    rx.breakpoints(sm=True, md=False, lg=False, xl=False),
                    rx.icon(tag=icon, size=16, color=GOLD),  # Small
                    rx.cond(
                        rx.breakpoints(md=True, lg=False, xl=False),
                        rx.icon(tag=icon, size=18, color=GOLD),  # Medium
                        rx.icon(tag=icon, size=20, color=GOLD),  # Large
                    ),
                ),
            ),
            rx.heading(
                title,
                font_size=["0.6em", "0.75em", "1em", "1.25em"],
                color=GOLD,
                weight="bold",
            ),
            align="center",
            spacing="1",
        ),
        rx.text(
            description,
            color="gray",
            font_size=["0.55em", "0.65em", "0.75em", "0.85em"],
            text_align="center",
            line_height="1.2",
        ),
        spacing="1",
        width="100%",
        padding="1",
    )


def home():
    return page_layout(
        rx.vstack(
            # Main content - centered vertically
            rx.center(
                rx.vstack(
                    rx.image(
                        src="/logonew.png",
                        width=["250px", "300px", "350px", "400px"],
                        height="auto",
                    ),
                    rx.image(
                        src="/word.png",
                        width=["250px", "300px", "350px", "400px"],
                        height="auto",
                    ),
                    rx.heading(
                        "Smart Event Management",
                        font_size=["0.9em", "1.1em", "1.4em", "1.8em"],
                        color=GOLD,
                        text_align="center",
                        weight="bold",
                        line_height="1.2",
                    ),
                    rx.text(
                        "Automated solutions for the elite.",
                        color="gray",
                        font_size=["0.55em", "0.65em", "0.8em", "1em"],
                        text_align="center",
                        line_height="1.3",
                    ),
                    rx.hstack(
                        rx.button(
                            "Get Started",
                            on_click=rx.redirect("/products"),
                            **button_style(),
                            font_size=["0.55em", "0.65em", "0.75em", "0.85em"],
                            padding=["0.15em 0.5em", "0.25em 0.7em", "0.35em 0.9em", "0.45em 1.1em"],
                        ),
                        rx.button(
                            "Contact Us",
                            on_click=rx.redirect("/contact"),
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            bg="transparent",
                            font_size=["0.55em", "0.65em", "0.75em", "0.85em"],
                            padding=["0.15em 0.5em", "0.25em 0.7em", "0.35em 0.9em", "0.45em 1.1em"],
                            _hover={"bg": GOLD, "color": BLACK},
                        ),
                        spacing="3",
                        flex_wrap="wrap",
                        justify="center",
                        width="100%",
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                    max_width="600px",
                ),
                width="100%",
                flex="1",
                padding=["0.5em", "0.8em", "1em", "1.2em"],
            ),

            # Features grid - Always at bottom
            rx.grid(
                feature_card("zap", "Fast", "Real-time check-ins."),
                feature_card("lock", "Secure", "Enterprise-grade security."),
                feature_card("mail", "Smart", "Automated QR code emails."),
                feature_card("gift", "Lucky Draw", "Engage & manage lucky draws."),
                columns=rx.breakpoints(initial="2", sm="2", md="4"),
                spacing=rx.breakpoints(initial="2", sm="2", md="3"),
                width="100%",
                padding=["0.3em", "0.5em", "0.8em", "1em"],
                **card_style(),
            ),

            spacing="0",
            width="100%",
            height="100%",
            justify="between",
        ),
    )