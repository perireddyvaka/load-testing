# Concurrent Load Testing Scripts

This directory contains scripts to run GET, POST, and PUT load tests simultaneously against your platform.

## Files

1. **Individual Test Files:**
   - `step-function-get.py` - GET operations test
   - `Step-function-post.py` - POST operations test  
   - `step-function-put.py` - PUT operations test

2. **Concurrent Test Runners:**
   - `run_all_tests.py` - Python script to run all tests concurrently
   - `run_all_tests.sh` - Bash script to run all tests concurrently
   - `test_config.conf` - Configuration file (for reference)

## Prerequisites

1. **Install Locust:**
   ```bash
   pip install locust
   ```

2. **Verify your test files are working individually:**
   ```bash
   locust -f step-function-get.py --host=http://10.2.16.116:8610
   ```

## Usage

### Option 1: Using Python Script (Recommended)

```bash
cd /home/perireddy/ctOP/locust-test/om2m-comparison/step-function
python3 run_all_tests.py
```

### Option 2: Using Bash Script

```bash
cd /home/perireddy/ctOP/locust-test/om2m-comparison/step-function
./run_all_tests.sh
```

## What the Scripts Do

1. **Start 3 concurrent Locust tests:**
   - GET test on port 8089 (2 hours duration)
   - POST test on port 8090 (2 hours duration)
   - PUT test on port 8091 (30 minutes duration)

2. **Generate separate outputs for each test:**
   - HTML reports
   - CSV statistics
   - Log files

3. **Provide Web UI access:**
   - GET Test: http://localhost:8089
   - POST Test: http://localhost:8090
   - PUT Test: http://localhost:8091

## Test Configuration

Each test runs with:
- **50 concurrent users** per test (150 total across all tests)
- **5 users/second spawn rate**
- **Step function load pattern** (gradually increasing load)

## Monitoring

1. **Real-time monitoring:**
   - Open the web UI URLs in your browser
   - Watch the console output for real-time logs

2. **Stopping tests:**
   - Press `Ctrl+C` to stop all tests gracefully
   - All processes will be terminated properly

## Output Files

Results are saved in a timestamped directory:
```
results_YYYYMMDD_HHMMSS/
├── get_test_report.html
├── get_test_stats.csv
├── get_test_stats_failures.csv
├── get_test_stats_exceptions.csv
├── post_test_report.html
├── post_test_stats.csv
├── post_test_stats_failures.csv
├── post_test_stats_exceptions.csv
├── put_test_report.html
├── put_test_stats.csv
├── put_test_stats_failures.csv
├── put_test_stats_exceptions.csv
└── *.log files
```

## Customization

### Modify test parameters:

1. **Edit the Python script** (`run_all_tests.py`):
   - Change `users`, `spawn_rate`, `time` in `test_configs`

2. **Edit the bash script** (`run_all_tests.sh`):
   - Modify variables at the top of the script

### Common modifications:
- **Increase users:** Change `--users=50` to `--users=100`
- **Change duration:** Modify `--run-time=120m` to `--run-time=60m`
- **Adjust spawn rate:** Change `--spawn-rate=5` to `--spawn-rate=10`

## Troubleshooting

1. **Port conflicts:**
   - If ports 8089-8091 are in use, modify the port numbers in the scripts

2. **Permission errors:**
   - Make sure the bash script is executable: `chmod +x run_all_tests.sh`

3. **Locust not found:**
   - Install locust: `pip install locust`
   - Check PATH: `which locust`

4. **Test failures:**
   - Check your server is running on http://10.2.16.116:8610
   - Verify authentication tokens are valid
   - Check individual test files work first

## Example Output

```
========================================
🎯 CONCURRENT LOAD TESTING STARTED
========================================
⏰ Start Time: 2025-09-08 14:30:00

📋 GET_Test:
   - File: step-function-get.py
   - Users: 50
   - Spawn Rate: 5/sec
   - Duration: 120m
   - Web UI: http://localhost:8089

📋 POST_Test:
   - File: Step-function-post.py
   - Users: 50
   - Spawn Rate: 5/sec
   - Duration: 120m
   - Web UI: http://localhost:8090

📋 PUT_Test:
   - File: step-function-put.py
   - Users: 50
   - Spawn Rate: 5/sec
   - Duration: 30m
   - Web UI: http://localhost:8091

🚀 All tests started! Press Ctrl+C to stop all tests.
```
