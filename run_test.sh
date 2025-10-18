#!/bin/bash

# Quick test runner for Locust load testing
# Usage: ./run_test.sh [duration_minutes] [spawn_rate]

DURATION=${1:-5}  # Default: 5 minutes
SPAWN_RATE=${2:-10}  # Default: 10 users/second

echo "================================================"
echo "Starting Locust Load Test - Continuous Posting"
echo "================================================"
echo "Duration: ${DURATION} minutes"
echo "Users: 50 (one per node)"
echo "Spawn Rate: ${SPAWN_RATE} users/second"
echo "Posting: Continuous (0.1-0.5s between posts)"
echo "Guarantee: Each node posts ≥1 time per 10 seconds"
echo "Expected RPS: 200-500+ requests/second"
echo "================================================"
echo ""

# Run locust
locust \
    -f locust_full_test.py \
    --users 50 \
    --spawn-rate ${SPAWN_RATE} \
    --headless \
    --run-time ${DURATION}m \
    --html report_$(date +%s).html \
    --csv results_$(date +%s)

echo ""
echo "================================================"
echo "Test completed! Check the generated HTML report."
echo "================================================"
