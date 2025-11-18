from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import json
import logging
import csv
import os
from datetime import datetime
from typing import Dict, Any
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('subscription_listener.log')
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Subscription Notification Listener",
    description="A robust listener for subscription notifications with comprehensive debugging",
    version="1.0.0"
)

# Statistics tracking
stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "start_time": datetime.now()
}

@app.get("/")
async def root():
    """Health check endpoint"""
    logger.info("Health check endpoint accessed")
    return {
        "status": "active",
        "service": "subscription-notification-listener",
        "uptime": str(datetime.now() - stats["start_time"]),
        "stats": stats
    }

@app.get("/stats")
async def get_stats():
    """Get listener statistics"""
    logger.info("Stats endpoint accessed")
    return {
        "statistics": stats,
        "uptime": str(datetime.now() - stats["start_time"])
    }

@app.post("/webhook")
@app.post("/notify")
@app.post("/subscription")
@app.post("/post")
async def subscription_listener(request: Request):
    """
    Main subscription notification listener endpoint
    Accepts POST requests and logs all details for debugging
    """
    stats["total_requests"] += 1
    request_id = f"req_{stats['total_requests']}_{datetime.now().strftime('%H%M%S')}"
    
    try:
        # Get client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        content_type = request.headers.get("content-type", "unknown")
        
        logger.info(f"[{request_id}] === INCOMING SUBSCRIPTION NOTIFICATION ===")
        logger.info(f"[{request_id}] Client IP: {client_ip}")
        logger.info(f"[{request_id}] User-Agent: {user_agent}")
        logger.info(f"[{request_id}] Content-Type: {content_type}")
        logger.info(f"[{request_id}] Method: {request.method}")
        logger.info(f"[{request_id}] URL: {request.url}")
        
        # Log all headers
        logger.info(f"[{request_id}] Headers:")
        for header_name, header_value in request.headers.items():
            logger.info(f"[{request_id}]   {header_name}: {header_value}")
        
        # Log query parameters if any
        if request.query_params:
            logger.info(f"[{request_id}] Query Parameters:")
            for param, value in request.query_params.items():
                logger.info(f"[{request_id}]   {param}: {value}")
        
        # Read and log raw body
        raw_body = await request.body()
        body_size = len(raw_body)
        logger.info(f"[{request_id}] Raw body size: {body_size} bytes")
        
        if body_size > 0:
            try:
                decoded_body = raw_body.decode('utf-8')
                logger.info(f"[{request_id}] Raw body (UTF-8): {decoded_body}")
            except UnicodeDecodeError:
                logger.warning(f"[{request_id}] Could not decode body as UTF-8, showing bytes")
                logger.info(f"[{request_id}] Raw body (bytes): {raw_body}")
        else:
            logger.info(f"[{request_id}] Empty body received")
        
        # Try to parse as JSON or form data; keep raw body available
        parsed_data = None
        raw_body_str = ''
        if body_size > 0:
            try:
                try:
                    raw_body_str = raw_body.decode('utf-8')
                except Exception:
                    # keep bytes representation if decode fails
                    raw_body_str = str(raw_body)

                # Make body available for downstream .json() or .form()
                request._body = raw_body

                # Attempt JSON first
                parsed_data = await request.json()
                logger.info(f"[{request_id}] Parsed JSON data:")
                logger.info(f"[{request_id}] {json.dumps(parsed_data, indent=2, default=str)}")

                # Extract common subscription fields if present
                subscription_fields = extract_subscription_info(parsed_data, request_id)
                if subscription_fields:
                    logger.info(f"[{request_id}] Subscription Info: {subscription_fields}")

            except json.JSONDecodeError as e:
                logger.warning(f"[{request_id}] Could not parse body as JSON: {e}")
                # Try to parse as form data
                try:
                    form_data = await request.form()
                    if form_data:
                        # Convert form data to a dict for storage
                        parsed_data = {k: v for k, v in form_data.items()}
                        logger.info(f"[{request_id}] Form data received:")
                        for key, value in parsed_data.items():
                            logger.info(f"[{request_id}]   {key}: {value}")
                except Exception as form_error:
                    logger.warning(f"[{request_id}] Could not parse as form data: {form_error}")
            except Exception as e:
                logger.error(f"[{request_id}] Error parsing request body: {e}")
                logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        # Prepare CSV record and print to terminal
        timestamp = datetime.now().isoformat()
        parsed_json_str = ''
        try:
            if parsed_data is not None:
                parsed_json_str = json.dumps(parsed_data, default=str)
        except Exception:
            parsed_json_str = str(parsed_data)

        # If raw_body_str not set earlier, decode now (could be empty)
        if not raw_body_str and body_size > 0:
            try:
                raw_body_str = raw_body.decode('utf-8')
            except Exception:
                raw_body_str = str(raw_body)

        # Print concise terminal output
        print(f"[{timestamp}] {request_id} - from {client_ip} ({content_type}) - size={body_size} bytes")
        if parsed_json_str:
            print(f"{request_id} - Parsed data: {parsed_json_str}")
        else:
            print(f"{request_id} - Raw body: {raw_body_str}")

        # Build a record for CSV
        record = {
            'timestamp': timestamp,
            'request_id': request_id,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'content_type': content_type,
            'body_size': body_size,
            'raw_body': raw_body_str,
            'parsed_json': parsed_json_str
        }

        # Try to save to CSV (errors logged but don't break response)
        save_notification_to_csv(record)

        # Log successful processing
        stats["successful_requests"] += 1
        logger.info(f"[{request_id}] === NOTIFICATION PROCESSED SUCCESSFULLY ===")

        # Return acknowledgment
        response_data = {
            "status": "received",
            "request_id": request_id,
            "timestamp": timestamp,
            "client_ip": client_ip,
            "body_size": body_size,
            "content_type": content_type,
            "message": "Subscription notification received and logged successfully"
        }

        if parsed_data:
            response_data["data_received"] = True

        logger.info(f"[{request_id}] Sending response: {response_data}")
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        stats["failed_requests"] += 1
        logger.error(f"[{request_id}] === ERROR PROCESSING NOTIFICATION ===")
        logger.error(f"[{request_id}] Error: {str(e)}")
        logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        error_response = {
            "status": "error",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Error processing subscription notification"
        }
        
        return JSONResponse(content=error_response, status_code=500)

def extract_subscription_info(data: Dict[Any, Any], request_id: str) -> Dict[str, Any]:
    """Extract common subscription-related fields from the payload"""
    try:
        subscription_info = {}
        
        # Common subscription fields to look for
        fields_to_extract = [
            'subscription_id', 'subscriptionId', 'id',
            'event_type', 'eventType', 'type', 'event',
            'user_id', 'userId', 'customer_id', 'customerId',
            'plan_id', 'planId', 'plan', 'subscription_plan',
            'status', 'subscription_status', 'state',
            'timestamp', 'created_at', 'updated_at',
            'amount', 'price', 'billing_amount',
            'currency', 'billing_currency',
            'webhook_id', 'webhookId', 'notification_id'
        ]
        
        def recursive_search(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if key.lower() in [f.lower() for f in fields_to_extract]:
                        subscription_info[full_key] = value
                    elif isinstance(value, (dict, list)):
                        recursive_search(value, full_key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    recursive_search(item, f"{prefix}[{i}]")
        
        recursive_search(data)
        return subscription_info
        
    except Exception as e:
        logger.warning(f"[{request_id}] Error extracting subscription info: {e}")
        return {}


CSV_FILE = 'received_notifications.csv'

def save_notification_to_csv(record: Dict[str, Any], csv_file: str = CSV_FILE) -> None:
    """Append a notification record (dict) to a CSV file. Create header if file missing."""
    try:
        # Ensure directory exists if path contains directories
        dir_name = os.path.dirname(os.path.abspath(csv_file))
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        file_exists = os.path.isfile(csv_file)
        # Use a stable column order
        fieldnames = [
            'timestamp', 'request_id', 'client_ip', 'user_agent', 'content_type',
            'body_size', 'raw_body', 'parsed_json'
        ]

        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            if not file_exists:
                writer.writeheader()
            # Ensure values are strings and not too large
            safe_record = {}
            for k in fieldnames:
                v = record.get(k, '')
                if v is None:
                    v = ''
                # Truncate very large bodies to keep CSV manageable
                if isinstance(v, str) and len(v) > 20000:
                    v = v[:20000] + '...[truncated]'
                safe_record[k] = v
            writer.writerow(safe_record)
    except Exception as e:
        logger.error(f"Error saving notification to CSV: {e}")
        logger.error(traceback.format_exc())

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    logger.warning(f"404 Not Found: {request.method} {request.url}")
    return JSONResponse(
        status_code=404,
        content={
            "status": "not_found",
            "message": "Endpoint not found. Available endpoints: /, /stats, /webhook, /notify, /subscription, /post",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "internal_error",
            "message": "Internal server error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    logger.info("Starting Subscription Notification Listener...")
    logger.info(f"Available endpoints:")
    logger.info(f"  GET  / - Health check")
    logger.info(f"  GET  /stats - Statistics")
    logger.info(f"  POST /webhook - Webhook notifications")
    logger.info(f"  POST /notify - Notification endpoint")
    logger.info(f"  POST /subscription - Subscription notifications")
    logger.info(f"  POST /post - Generic post endpoint")
    
    uvicorn.run(
        "listener:app", 
        host="0.0.0.0", 
        port=8010, 
        reload=False,
        log_level="warning"
    )