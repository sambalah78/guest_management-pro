import reflex as rx
from guest_management.styles.theme import WHITE, GOLD, DARK_GRAY, button_style, card_style, LIGHT_GRAY
from guest_management.pages import page_layout


def products_page() -> rx.Component:
    """Products page showcasing automated guest check-in solutions"""
    return page_layout(
        rx.vstack(
            # Header
            rx.center(
                rx.vstack(
                    rx.text(
                        "Our Products",
                        font_size="2.5rem",
                        font_weight="bold",
                        color=GOLD,
                        class_name="animate-fly-in",
                    ),
                    rx.text(
                        "Automated Guest Check-in Solutions",
                        font_size="1.2rem",
                        color=DARK_GRAY,
                        class_name="animate-fade-in",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                padding="1em 0",
            ),

            # Products Grid
            rx.grid(
                # Product 1: Corporate Events
                rx.card(
                    rx.vstack(
                        rx.icon("briefcase", size=60, color=GOLD),
                        rx.heading("Corporate Events", size="4", color=GOLD),
                        rx.text("Perfect for conferences, seminars, and company dinners", color=LIGHT_GRAY,
                                text_align="center", font_size="0.85rem"),
                        rx.divider(bg=GOLD),
                        rx.vstack(
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("QR Code Check-in", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Email Invitations", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Table Assignment", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Lucky Draw System", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Real-time Analytics", color=WHITE), spacing="2", align="center"),
                            align="start",
                            spacing="2",
                        ),
                        rx.button(
                            "Learn More",
                            on_click=rx.redirect("/contact"),
                            **button_style(),
                            width="100%",
                        ),
                        spacing="4",
                        align="center",
                    ),
                    **card_style(),
                ),

                # Product 2: Weddings
                rx.card(
                    rx.vstack(
                        rx.icon("heart", size=60, color=GOLD),
                        rx.heading("Weddings", size="4", color=GOLD),
                        rx.text("Create magical wedding experiences", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        rx.divider(bg=GOLD),
                        rx.vstack(
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Guest List Management", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Table Seating", color=WHITE),
                                      spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Dietary Preferences", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Plus-One Management", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Digital Invitations", color=WHITE), spacing="2", align="center"),
                            align="start",
                            spacing="2",
                        ),
                        rx.button(
                            "Learn More",
                            on_click=rx.redirect("/contact"),
                            **button_style(),
                            width="100%",
                        ),
                        spacing="4",
                        align="center",
                    ),
                    **card_style(),
                ),

                # Product 3: Sports Day
                rx.card(
                    rx.vstack(
                        rx.icon("activity", size=60, color=GOLD),
                        rx.heading("Sports Day", size="4", color=GOLD),
                        rx.text("Organize sports events effortlessly", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        rx.divider(bg=GOLD),
                        rx.vstack(
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Team Management", color=WHITE),
                                      spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Score Tracking", color=WHITE),
                                      spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Voucher System", color=WHITE),
                                      spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Parent Info Collection", color=WHITE), spacing="2", align="center"),
                            rx.hstack(rx.icon("circle_check", size=16, color=GOLD),
                                      rx.text("Medal Management", color=WHITE), spacing="2", align="center"),
                            align="start",
                            spacing="2",
                        ),
                        rx.button(
                            "Learn More",
                            on_click=rx.redirect("/contact"),
                            **button_style(),
                            width="100%",
                        ),
                        spacing="4",
                        align="center",
                    ),
                    **card_style(),
                ),
                columns=rx.breakpoints(initial="1", md="3"),
                spacing="4",
                width="100%",
                padding="0.5em 0",
            ),

            # Feature Comparison Table
            rx.card(
                rx.vstack(
                    rx.heading("Feature Comparison", size="4", color=GOLD, text_align="center"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Feature", color=GOLD),
                                rx.table.column_header_cell("Corporate Events", color=GOLD),
                                rx.table.column_header_cell("Weddings", color=GOLD),
                                rx.table.column_header_cell("Sports Day", color=GOLD),
                            )
                        ),
                        rx.table.body(
                            rx.table.row(
                                rx.table.cell("QR Check-in", color=WHITE),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                            ),
                            rx.table.row(
                                rx.table.cell("Email Invitations", color=WHITE),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                            ),
                            rx.table.row(
                                rx.table.cell("Table Management", color=WHITE),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("x", color="red")),
                            ),
                            rx.table.row(
                                rx.table.cell("Food Vouchers", color=WHITE),
                                rx.table.cell(rx.icon("x", color="red")),
                                rx.table.cell(rx.icon("x", color="red")),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                            ),
                            rx.table.row(
                                rx.table.cell("Lucky Draw", color=WHITE),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("x", color="red")),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                            ),
                            rx.table.row(
                                rx.table.cell("Plus-One Management", color=WHITE),
                                rx.table.cell(rx.icon("x", color="red")),
                                rx.table.cell(rx.icon("check", color=GOLD)),
                                rx.table.cell(rx.icon("x", color="red")),
                            ),
                        ),
                        variant="surface",
                        width="100%",
                    ),
                    spacing="4",
                ),
                **card_style(),
            ),

            # CTA
            rx.center(
                rx.button(
                    "Get Started Today",
                    on_click=rx.redirect("/contact"),
                    size="3",
                    **button_style(),
                ),
                width="100%",
                padding="2em",
            ),

            spacing="3",
            width="100%",
            padding="0.5em",
        )
    )