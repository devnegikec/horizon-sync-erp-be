#!/usr/bin/env python3
"""
Chart of Account Bug Validation Test Runner

This script runs the Chart of Account bug validation tests and generates a report
showing which issues are fixed and which still need attention.

Usage:
    python validate_coa_bugs.py [--verbose] [--issue=1,2,3,4,5]
"""

import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime


class TestResult:
    """Represents the result of running a test suite"""
    
    def __init__(self, name, description, command, result):
        self.name = name
        self.description = description 
        self.command = command
        self.result = result
        self.passed = result.returncode == 0
        

def run_test_suite(test_class, description, verbose=False):
    """Run a specific test suite and return results"""
    
    command = [
        sys.executable, "-m", "pytest", 
        f"tests/test_chart_of_accounts_bug_validation.py::{test_class}",
        "-v" if verbose else "-q",
        "--tb=short"
    ]
    
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if verbose:
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
                
        return TestResult(test_class, description, command, result)
        
    except Exception as e:
        print(f"Error running test: {e}")
        return None


def generate_report(test_results, output_file=None):
    """Generate a summary report of test results"""
    
    report_lines = []
    report_lines.append("CHART OF ACCOUNT BUG VALIDATION REPORT")
    report_lines.append("=" * 50)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r and r.passed)
    
    report_lines.append(f"SUMMARY: {passed_tests}/{total_tests} test suites passed")
    report_lines.append("")
    
    # Individual results
    for i, result in enumerate(test_results, 1):
        if not result:
            report_lines.append(f"Issue {i}: ERROR - Test failed to run")
            continue
            
        status = "✅ FIXED" if result.passed else "❌ STILL BROKEN"
        report_lines.append(f"Issue {i}: {status}")
        report_lines.append(f"  {result.description}")
        
        if not result.passed:
            # Extract key error info from output
            if result.result.stdout:
                lines = result.result.stdout.split('\n')
                # Find the FAILURES section
                in_failures = False
                for line in lines:
                    if "FAILURES" in line or "failed" in line.lower():
                        in_failures = True
                    if in_failures and line.strip():
                        report_lines.append(f"    {line}")
                        if "short test summary" in line.lower():
                            break
        
        report_lines.append("")
    
    # Overall status
    report_lines.append("RECOMMENDATIONS:")
    if passed_tests == total_tests:
        report_lines.append("🎉 All Chart of Account issues appear to be fixed!")
        report_lines.append("   Consider running these tests in your CI pipeline to prevent regression.")
    else:
        remaining_issues = total_tests - passed_tests
        report_lines.append(f"⚠️  {remaining_issues} issue(s) still need attention.")
        report_lines.append("   Review the failed test output above for details.")
        report_lines.append("   Run individual test suites for more detailed debugging.")
    
    report_lines.append("")
    report_lines.append("For detailed debugging, run:")
    report_lines.append("  python validate_coa_bugs.py --verbose")
    report_lines.append("")
    
    # Output report
    report_text = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"\nReport saved to: {output_file}")
    else:
        print("\n" + report_text)
    
    return passed_tests == total_tests


def main():
    parser = argparse.ArgumentParser(description='Validate Chart of Account bug fixes')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed test output')
    parser.add_argument('--issues', type=str,
                       help='Comma-separated list of issue numbers to test (1-5)')
    parser.add_argument('--output', type=str,
                       help='Save report to file')
    
    args = parser.parse_args()
    
    # Define test suites for each issue
    test_suites = [
        ("TestChartOfAccountBalancePopulation", "Issue 1: Balance not populating in UI"),
        ("TestChartOfAccountHierarchyLevels", "Issue 2: Level hierarchy not populating"),
        ("TestChartOfAccountGroupHierarchy", "Issue 3: Group hierarchy not populating"),
        ("TestChartOfAccountPagination", "Issue 4: Pagination not working"),
        ("TestEditAccountDialogParentName", "Issue 5: Parent account name not showing in edit dialog")
    ]
    
    # Filter by specific issues if requested
    if args.issues:
        try:
            issue_numbers = [int(x.strip()) for x in args.issues.split(',')]
            test_suites = [test_suites[i-1] for i in issue_numbers if 1 <= i <= len(test_suites)]
        except (ValueError, IndexError) as e:
            print(f"Error: Invalid issue numbers. Use 1-5. Error: {e}")
            return 1
    
    print("Chart of Account Bug Validation Test Runner")
    print("=" * 50)
    print(f"Testing {len(test_suites)} issue(s)...")
    
    # Run all test suites
    results = []
    for test_class, description in test_suites:
        result = run_test_suite(test_class, description, args.verbose)
        results.append(result)
    
    # Generate report
    all_passed = generate_report(results, args.output)
    
    # Return appropriate exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())