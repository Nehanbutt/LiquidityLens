
from modules.input_handler import get_user_inputs
from modules.output_formatter import generate_report
from modules.simulator import find_max_safe_loan, simulate_cashflow
from modules.validator import ValidationError, validate_inputs


def main() -> int:
    print("=" * 72)
    print("Cashflow Loan Planner")
    print("=" * 72)
    print("Enter the business and loan details below.\n")

    try:
        raw_data = get_user_inputs()
        validated_data = validate_inputs(raw_data)
        results = simulate_cashflow(validated_data)
        print("\n" + generate_report(results))

        max_safe_loan = find_max_safe_loan(validated_data)
        print(f"\nEstimated maximum SAFE loan: {max_safe_loan:,.2f}")
        return 0
    except ValidationError as exc:
        print("Input validation failed:")
        for issue in exc.errors:
            print(f" - {issue}")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
