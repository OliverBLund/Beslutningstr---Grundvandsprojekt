"""
Standardized reporting utilities for workflow steps.

Provides consistent, clean console output across all steps while preserving
essential information for understanding data transformations and filtering.
"""


def report_step_header(step_num: int, step_name: str, width: int = 80):
    """Print standardized step header."""
    print("\n" + "=" * width)
    print(f"STEP {step_num}: {step_name}")
    print("=" * width)


def report_subsection(title: str, width: int = 80, char: str = "─"):
    """Print subsection divider."""
    print("\n" + char * width)
    print(title)
    print(char * width)


def report_counts(label: str, sites: int = None, gvfks: int = None, combinations: int = None, indent: int = 0):
    """Print standardized counts with optional indent."""
    prefix = "  " * indent
    parts = []
    if combinations is not None:
        parts.append(f"{combinations:,} combinations")
    if sites is not None:
        parts.append(f"{sites:,} sites")
    if gvfks is not None:
        parts.append(f"{gvfks:,} GVFKs")

    if parts:
        print(f"{prefix}{label}: {', '.join(parts)}")


def report_filtering(filtered_count: int, total_count: int, reason: str, indent: int = 0):
    """Report filtering with reason."""
    prefix = "  " * indent
    if total_count > 0:
        pct = (filtered_count / total_count) * 100
        print(f"{prefix}FILTERED: {filtered_count:,} / {total_count:,} ({pct:.1f}%) - {reason}")
    else:
        print(f"{prefix}FILTERED: {filtered_count:,} - {reason}")


def report_input_output(input_dict: dict, output_dict: dict, indent: int = 0):
    """
    Report input and output counts in standardized format.

    Args:
        input_dict: {'sites': N, 'gvfks': N, 'combinations': N}
        output_dict: {'sites': N, 'gvfks': N, 'combinations': N}
    """
    prefix = "  " * indent
    print(f"\n{prefix}INPUT:")
    report_counts("",
                 sites=input_dict.get('sites'),
                 gvfks=input_dict.get('gvfks'),
                 combinations=input_dict.get('combinations'),
                 indent=indent+1)

    print(f"\n{prefix}OUTPUT:")
    report_counts("",
                 sites=output_dict.get('sites'),
                 gvfks=output_dict.get('gvfks'),
                 combinations=output_dict.get('combinations'),
                 indent=indent+1)

    # Calculate filtered amounts
    if input_dict.get('combinations') and output_dict.get('combinations'):
        filtered = input_dict['combinations'] - output_dict['combinations']
        if filtered > 0:
            pct = (filtered / input_dict['combinations']) * 100
            print(f"\n{prefix}  Filtered: {filtered:,} combinations ({pct:.1f}%)")


def report_breakdown(title: str, items: dict, indent: int = 0):
    """
    Report categorical breakdown.

    Args:
        title: Section title
        items: Dict of {category: count}
    """
    prefix = "  " * indent
    print(f"{prefix}{title}:")
    for category, count in items.items():
        if isinstance(count, tuple):
            # Support (count, percentage) tuples
            print(f"{prefix}  ├─ {category}: {count[0]:,} ({count[1]:.1f}%)")
        else:
            print(f"{prefix}  ├─ {category}: {count:,}")


def report_statistics(stats: dict, indent: int = 0):
    """Report key statistics in clean format."""
    prefix = "  " * indent
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{prefix}{key}: {value:,.1f}")
        elif isinstance(value, int):
            print(f"{prefix}{key}: {value:,}")
        else:
            print(f"{prefix}{key}: {value}")


def report_completion(step_num: int):
    """Print step completion marker."""
    print(f"\nStep {step_num} complete")
