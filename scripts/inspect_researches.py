
from src.ui.runtime import get_all_researches

researches = get_all_researches()

for research in researches:
    print("\n" + "=" * 60)

    if isinstance(research, dict):
        for key in (
            "run_id",
            "status",
            "current_stage",
            "created_at",
            "updated_at",
            "report_version_id",
            "approval_decision",
            "delivery_status",
            "stop_reason",
        ):
            print(f"{key}: {research.get(key)}")
    else:
        print(research)
