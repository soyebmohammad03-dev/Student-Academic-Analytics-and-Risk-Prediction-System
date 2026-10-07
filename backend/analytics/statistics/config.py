"""Fixed settings shared by every statistical analysis."""

#: Significance threshold for all tests (two-sided).
ALPHA = 0.05
#: Confidence level for all confidence intervals.
CONFIDENCE = 0.95
#: Groups smaller than this are flagged; inference on them is unreliable.
MIN_GROUP_SIZE = 10
#: Minimum per-group n at which moderate skew is tolerated for mean-based tests (CLT).
LARGE_SAMPLE = 30
#: |skewness| at or below which a large group is treated as adequate for mean tests.
MAX_ABS_SKEW = 1.0
#: Tukey fence multiplier for IQR outlier detection.
IQR_MULTIPLIER = 1.5
#: |z| above which a value is flagged by the standardised-score rule.
Z_THRESHOLD = 3.0
