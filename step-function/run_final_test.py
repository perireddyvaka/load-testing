#!/usr/bin/env python3
"""
FINAL TEST RUNNER - All Issues Fixed
Run this for the complete fixed version
"""

import subprocess
import sys
import os

def run_final_test():
    print("=" * 80)
    print("🚀 FINAL COMBINED LOAD TEST - ALL ISSUES FIXED")
    print("=" * 80)
    print("🔧 FIXES APPLIED:")
    print("   ✅ Updated Bearer Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTc5MzA0NDIsInN1YiI6IjEyIn0.Ca4meTua6KYpMHPFBRR9dLwaycUOC1dFd235tVn1wKA")
    print("   ✅ Fixed CIN Token: 26d545994f733631df36c50b331213fd")
    print("   ✅ Fixed /nodes/fetch-node-data endpoints (401 errors)")
    print("   ✅ Fixed /subscription/get-user-subscriptions endpoint path")
    print("   ✅ Fixed /verticals/create-ae payload format (422 errors)")
    print("   ✅ Added missing /alarms/un-read endpoint")
    print("   ✅ Fixed /stats/loners authentication")
    print("   ✅ Dynamic IoT vertical names and incremental IDs")
    print()
    print("📊 Test Configuration:")
    print("   - GET requests (50%) - All endpoints with proper auth")
    print("   - POST requests (30%) - Fixed payload formats")  
    print("   - PUT requests (20%) - Update operations")
    print()
    print("🌐 Web UI: http://localhost:8089")
    print("⏰ Duration: 2 hours")
    print("👥 Users: 150")
    print("📈 Spawn Rate: 10/sec")
    print("=" * 80)
    
    try:
        # Build and run locust command
        cmd = [
            'locust',
            '-f', 'final_combined_test.py',
            '--host', 'http://10.2.16.116:8610',
            '--users', '150',
            '--spawn-rate', '10',
            '--run-time', '120m',
            '--web-port', '8089',
            '--html', 'final_test_report.html',
            '--csv', 'final_test_stats'
        ]
        
        print(f"🚀 Running command: {' '.join(cmd)}")
        print()
        
        # Change to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Start the process
        process = subprocess.run(cmd, check=True)
        
        print("\n✅ Test completed successfully!")
        print("📊 Check final_test_report.html for detailed results")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_final_test()
