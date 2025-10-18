# Locust Load Testing for Node API

This Locust test script simulates 50 nodes continuously posting data to the API.

## Features

- **Deterministic Node Assignment**: Each spawned user is assigned a unique node ID (1-50) sequentially
- **Immediate Posting**: All 50 nodes start posting from second 1 (immediate post on startup)
- **Continuous Posting**: Each node posts continuously throughout the test
- **10-Second Guarantee**: Every node is guaranteed to post at least once within every 10-second window
- **Continuous Fetch**: Separate task that continuously fetches node data independently
- **High Request Rate**: With wait time between 0.1-0.5 seconds, each node can post 2-10 times per second

## Requirements

```bash
pip install locust
```

## Usage

### Basic Run (50 nodes, continuous posting)

```bash
locust -f locust_full_test.py --users 50 --spawn-rate 10
```

Then open http://localhost:8089 in your browser to access the Locust web UI.

### Headless Mode (no web UI)

```bash
locust -f locust_full_test.py --users 50 --spawn-rate 10 --headless --run-time 5m
```

### Quick Test (spawn all 50 users immediately)

```bash
locust -f locust_full_test.py --users 50 --spawn-rate 50 --headless --run-time 2m
```

## How It Works

### Node Assignment
- Uses a shared counter with gevent semaphore for thread-safe assignment
- First 50 users get node IDs 1-50 sequentially
- If more than 50 users are spawned, IDs wrap around

### Payload Selection
- Nodes 1-25: Use `crowd_payload` (crowd monitoring data)
- Nodes 26-50: Use `energy_payload` (energy monitoring data)

### Posting Behavior
1. **Immediate Start**: Each node posts immediately when spawned (within the first second)
2. **Continuous Posting**: Nodes keep posting with random wait times between 0.1-0.5 seconds
3. **10-Second Guarantee**: Logic ensures each node posts at least once every 10 seconds
4. **High Throughput**: Each node can post 2-10 times per second depending on server response time

### Task Distribution
- **`post_node_data` (weight: 10)**: Posts data continuously to `/nodes/create-cin/{node_id}`
  - Runs 10x more frequently than fetch
  - Guarantees posting every 10 seconds minimum
- **`fetch_node_data` (weight: 1)**: Continuously fetches data from `/nodes/fetch-node-data/`
  - Runs independently as a separate task
  - No dependency on post timing

### Expected RPS
With 50 users and `wait_time = between(0.1, 0.5)`:
- **Minimum**: ~100 requests/second (50 users × 2 requests/second average)
- **Typical**: ~200-400 requests/second (depending on server response time)
- **POST vs FETCH Ratio**: Approximately 10:1 (due to task weights)

## Configuration

### Modifying Host
Edit line 85 in `locust_full_test.py`:
```python
host = "http://10.2.16.116:8610"
```

### Adjusting Wait Time
Edit line 89 in `locust_full_test.py`:
```python
wait_time = between(0.1, 0.5)  # Random wait between 0.1-0.5 seconds
```

To change posting frequency:
- **Faster posting**: `between(0.05, 0.2)` - More aggressive
- **Slower posting**: `between(0.5, 2)` - Less aggressive
- **Fixed interval**: `constant(0.3)` - Post every 0.3 seconds

### Modifying 10-Second Guarantee
Edit the condition in `post_node_data` method:
```python
if now - self._last_post >= 10:  # Change 10 to your desired interval
```

## Monitoring

During the test, Locust provides:
- Real-time RPS (requests per second)
- Response times (min/max/average/percentiles)
- Failure rates
- Number of active users
- Request distribution (POST vs GET)

## Example Commands

```bash
# Quick 1-minute aggressive test with all 50 users spawned immediately
locust -f locust_full_test.py --users 50 --spawn-rate 50 --headless --run-time 1m

# 10-minute sustained load test with HTML report
locust -f locust_full_test.py --users 50 --spawn-rate 10 --headless --run-time 10m --html report.html

# 5-minute test with CSV output for analysis
locust -f locust_full_test.py --users 50 --spawn-rate 10 --headless --run-time 5m --csv results
```

## Verification

To verify the "at least once every 10 seconds" requirement:
1. Run the test for at least 30 seconds
2. Check Locust stats for POST requests
3. Calculate: `Total POST requests / (Test duration in seconds / 10) / 50`
4. Result should be ≥ 1.0 (confirming each node posted at least once per 10-second window)

Example:
- Test duration: 60 seconds
- Total POST requests: 12,000
- Calculation: 12,000 / (60/10) / 50 = 12,000 / 6 / 50 = 40 posts per node per 10-second window ✅

## Troubleshooting

### RPS is too high/server overloaded
- Increase wait time: `wait_time = between(0.5, 1.5)`
- Reduce number of users
- Increase spawn rate delay: `--spawn-rate 5` (slower ramp-up)

### RPS is too low/not meeting requirements
- Decrease wait time: `wait_time = between(0.05, 0.2)`
- Check server response times (may be bottleneck)
- Verify network connectivity

### Not all nodes posting within 10 seconds
- Check the logs for errors
- Verify server can handle the load
- Check that all 50 users were spawned successfully

### Import errors
```bash
pip install locust gevent
```

### Authentication errors
- Verify tokens in `node_tokens` dictionary are valid
- Check `fetch_token` is not expired

## Performance Characteristics

**Expected behavior with 50 users:**
- All 50 nodes start posting immediately (within first 2-3 seconds)
- Each node posts continuously every 0.1-0.5 seconds
- Minimum guaranteed: 1 post per node every 10 seconds
- Typical: 5-20 posts per node every 10 seconds (depending on server response time)
- Fetch requests run independently and continuously
- POST:FETCH ratio approximately 10:1
