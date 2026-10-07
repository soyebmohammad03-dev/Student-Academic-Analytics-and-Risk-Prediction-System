"""Fixed configuration for reproducible preprocessing and splitting."""

#: Seed for every random operation in preprocessing (train/test splitting).
RANDOM_STATE = 42
#: Share of each cohort held out as the test set.
TEST_SIZE = 0.2
#: Pass mark on the Portuguese 0–20 scale. Academic risk is defined as G3 below it.
RISK_THRESHOLD = 10
