def test_parse_pre_draw_winners_file():
    import io
    import pandas as pd

    from guest_management.services.excel_service_ranked import ExcelService

    df = pd.DataFrame(
        [
            {
                "Name": "Sarah Lim",
                "ID": "G002",
                "Prize": "AirPods Pro",
                "Value": "RM 999",
                "Image": "https://example.com/airpods.jpg",
            },
            {
                "Name": "John Tan",
                "ID": "G005",
                "Prize": "Smart Watch",
                "Value": "RM 699",
                "Image": "",
            },
        ]
    )

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    winners = ExcelService().parse_pre_draw_winners_file(
        output.getvalue()
    )

    assert len(winners) == 2

    assert winners[0]["name"] == "Sarah Lim"
    assert winners[0]["guest_id"] == "G002"
    assert winners[0]["prize_name"] == "AirPods Pro"
    assert winners[0]["prize_value"] == "RM 999"
    assert winners[0]["image_url"] == "https://example.com/airpods.jpg"


def test_parse_pre_draw_winners_requires_id():
    import io
    import pandas as pd
    import pytest

    from guest_management.services.excel_service_ranked import ExcelService

    df = pd.DataFrame(
        [
            {
                "Name": "Sarah Lim",
                "Prize": "AirPods Pro",
            }
        ]
    )

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    with pytest.raises(ValueError, match="ID"):
        ExcelService().parse_pre_draw_winners_file(
            output.getvalue()
        )


def test_parse_pre_draw_winners_rejects_duplicate_ids():
    import io
    import pandas as pd
    import pytest

    from guest_management.services.excel_service_ranked import ExcelService

    df = pd.DataFrame(
        [
            {"Name": "Sarah Lim", "ID": "G002"},
            {"Name": "Another Sarah", "ID": "G002"},
        ]
    )

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    with pytest.raises(ValueError, match="Duplicate participant ID"):
        ExcelService().parse_pre_draw_winners_file(
            output.getvalue()
        )