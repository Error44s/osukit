from osukit import load_golden_cases, optimize_standard_tuning

cases = load_golden_cases('tests/data/sample_golden_cases.json')
outcome = optimize_standard_tuning(cases)

print('Suggested tuning:', outcome.tuning)
print('Average relative error:', outcome.average_relative_error)
print('Max relative error:', outcome.max_relative_error)
